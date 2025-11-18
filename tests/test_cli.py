from shoply_bot.cli import handle_user_input
from shoply_bot.faq import FAQItem
from shoply_bot.orders import Order
from shoply_bot.session import JsonlLogger, SessionState


class FakeResponse:
    def __init__(self, text: str, usage=None):
        self.content = text
        self.usage_metadata = usage or {
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
        }

class FakeChain:
    def __init__(self, text: str):
        self.text = text
        self.last_input = None
        self.last_config = None

    def invoke(self, inp, config):
        self.last_input = inp
        self.last_config = config
        return FakeResponse(self.text)

def test_order_found_updates_context(tmp_path):
    # подготовка state с временным логом
    from shoply_bot.session import SessionState, JsonlLogger
    log = JsonlLogger(tmp_path / "log.jsonl")
    state = SessionState(session_id="test", brand="Shoply", model="gpt", logger=log)

    orders = {"123": Order(id="123", payload={"status": "in_transit", "eta_days": 2})}
    faq_items = []  # не нужен здесь
    chain = FakeChain("ignored")

    should_exit, reply = handle_user_input(
        "/order 123", state, chain, faq_items, orders
    )

    assert not should_exit
    assert "Заказ 123" in reply

    assert "Информация о заказе клиента" in state.last_order_context
    assert "Заказ 123 в пути" in state.last_order_context
    assert "Ориентировочный срок доставки: 2 дн." in state.last_order_context

def test_faq_path_calls_chain(tmp_path):
    log = JsonlLogger(tmp_path / "log.jsonl")
    state = SessionState(session_id="test", brand="Shoply", model="gpt", logger=log)

    faq_items = [FAQItem("Как оформить возврат?", "Верните в течение 14 дней.")]
    orders = {}
    chain = FakeChain("Краткий ответ.")

    should_exit, reply = handle_user_input(
        "как вернуть товар?", state, chain, faq_items, orders
    )

    assert not should_exit
    assert reply == "Краткий ответ."
    assert "question" in chain.last_input
    assert "context" in chain.last_input
    assert chain.last_config["configurable"]["session_id"] == "test"
