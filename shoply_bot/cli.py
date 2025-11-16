# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

from datetime import datetime

from openai import OpenAI

from .config import Settings, DATA_DIR, LOGS_DIR
from .faq import load_faq, find_top_faq_matches, build_faq_context
from .orders import load_orders, get_order, build_order_context
from .session import SessionState
from .llm import ChatModel


def run_bot():
    settings = Settings.load()
    faq_items = load_faq(DATA_DIR / "faq.json")
    orders = load_orders(DATA_DIR / "orders.json")

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"session_{session_id}.jsonl"

    state = SessionState(
        session_id=session_id,
        brand=settings.brand_name,
        model=settings.openai_model,
        log_path=log_path,
    )
    state.init_meta()

    client = OpenAI(api_key=settings.openai_api_key)
    model = ChatModel(client, settings.openai_model, settings.brand_name)

    print(f"{settings.brand_name} support bot. /order <id>, /exit для выхода.")

    while True:
        try:
            user_input = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nБот: Хорошего дня!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "exit", "/quit", "quit"):
            print("Бот: Хорошего дня!")
            state.log_event("user", user_input)
            state.log_event("assistant", "Хорошего дня!", extra={"note": "session_end"})
            break

        state.log_event("user", user_input)
        state.add_history("user", user_input)

        # /order
        if user_input.startswith("/order"):
            parts = user_input.split()
            if len(parts) != 2:
                answer = "Корректный формат: /order <id>."
            else:
                order_id = parts[1]
                order = get_order(orders, order_id)
                if not order:
                    answer = f"Заказ {order_id} не найден. Проверьте номер или обратитесь к оператору."
                    state.last_order_context = None
                else:
                    answer = build_order_context(order).splitlines()[0]  # первая строка для пользователя
                    state.last_order_context = build_order_context(order)

            print(f"Бот: {answer}")
            state.log_event("assistant", answer, extra={"source": "orders"})
            state.add_history("assistant", answer)
            continue

        # RAG по FAQ
        matches = find_top_faq_matches(user_input, faq_items)
        faq_context = build_faq_context(matches)

        reply, usage = model.reply(
            user_message=user_input,
            faq_context=faq_context,
            order_context=state.last_order_context,
            history=state.history,
        )

        print(f"Бот: {reply}")

        state.log_event("assistant", reply, usage=usage, extra={"source": "faq" if matches else "no_faq"})
        state.log_usage_step(usage)
        state.add_history("assistant", reply)

    # итоговая сводка по usage
    state.log_usage_summary()
