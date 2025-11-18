# SPDX-License-Identifier: CC0-1.0
from datetime import datetime
from typing import Protocol

from .config import Settings, DATA_DIR, LOGS_DIR
from .faq import load_faq, find_top_faq_matches, build_faq_context
from .orders import load_orders, get_order, build_order_context, format_order_status
from .session import SessionState, JsonlLogger
from .llm import build_chain

class SupportsInvoke(Protocol):
    def invoke(self, inp: dict, config: dict) -> object: ...


def handle_user_input(
        user_input: str,
        state: SessionState,
        chain_with_history: SupportsInvoke,
        faq_items,
        orders,
) -> tuple[bool, str | None]:
    if not user_input:
        return False, None

    if user_input.lower() in ("/exit", "exit", "/quit", "quit"):
        state.log_event("user", user_input)
        state.log_event("assistant", "Хорошего дня!", extra={"note": "session_end"})
        return True, "Хорошего дня!"

    if user_input.startswith("/order"):
        parts = user_input.split()
        if len(parts) != 2:
            answer = "Корректный формат: /order <id>."
            state.last_order_context = None
        else:
            order_id = parts[1]
            order = get_order(orders, order_id)
            if not order:
                answer = f"Заказ {order_id} не найден. Проверьте номер или обратитесь к оператору."
                state.last_order_context = None
            else:
                state.last_order_context = build_order_context(order)
                answer = format_order_status(order)

        state.log_event("assistant", answer, extra={"source": "orders"})
        state.add_history("assistant", answer)
        return False, answer

    # RAG по FAQ
    matches = find_top_faq_matches(user_input, faq_items)
    full_ctx = build_faq_context(matches)
    if state.last_order_context:
        full_ctx += "\n\n" + state.last_order_context

    try:
        response = chain_with_history.invoke(
            {"question": user_input, "context": full_ctx},
            {"configurable": {"session_id": state.session_id}},
        )
    except Exception as e:
        err_text = f"Ошибка LLM: {e}"
        state.log_event("assistant", err_text, source="error")
        state.add_history("assistant", err_text)
        return False, err_text

    reply = response.content.strip()
    usage_meta = getattr(response, "usage_metadata", None)
    usage = None
    if usage_meta:
        usage = {
            "prompt_tokens": usage_meta.get("prompt_tokens", 0),
            "completion_tokens": usage_meta.get("completion_tokens", 0),
            "total_tokens": usage_meta.get("total_tokens", 0),
        }
        state.log_usage_step(usage)

    state.log_event("assistant", reply, usage=usage, source="faq" if matches else "no_faq")
    state.add_history("assistant", reply)
    return False, reply


def run_bot(input_fn=input, print_fn=print):
    settings = Settings.load()
    faq_items = load_faq(DATA_DIR / "faq.json")
    orders = load_orders(DATA_DIR / "orders.json")

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"session_{session_id}.jsonl"
    state = SessionState(
        session_id=session_id,
        brand=settings.brand_name,
        model=settings.openai_model,
        logger=JsonlLogger(log_path),
    )
    state.init_meta()

    chain_with_history, _ = build_chain(
        model_name=settings.openai_model,
        brand=settings.brand_name,
    )

    print_fn(f"{settings.brand_name} support bot. /order <id>, /exit для выхода.")

    while True:
        try:
            user_input = input_fn("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print_fn("\nБот: Хорошего дня!")
            break

        should_exit, reply = handle_user_input(
            user_input=user_input,
            state=state,
            chain_with_history=chain_with_history,
            faq_items=faq_items,
            orders=orders,
        )

        if reply is not None:
            print_fn(f"Бот: {reply}")
        if should_exit:
            break

    # итоговая сводка по usage
    state.log_usage_summary()
