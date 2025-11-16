# SPDX-License-Identifier: CC0-1.0

from shoply_bot.orders import Order, format_order_status, build_order_context


def test_format_order_in_transit():
    order = Order(id="123", payload={"status": "in_transit", "eta_days": 2, "carrier": "X"})
    text = format_order_status(order)
    assert "в пути" in text.lower()
    assert "2 дн" in text
    assert "X" in text


def test_format_order_processing_has_note():
    order = Order(id="555", payload={"status": "processing", "note": "Ожидает комплектации"})
    text = format_order_status(order)
    assert "в обработке" in text.lower()
    assert "Ожидает комплектации" in text


def test_build_order_context_includes_json():
    payload = {"status": "delivered", "delivered_at": "2025-08-10"}
    order = Order(id="987", payload=payload)
    ctx = build_order_context(order)
    assert "Информация о заказе" in ctx
    assert "2025-08-10" in ctx
    assert "delivered" in ctx
