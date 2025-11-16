# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class Order:
    id: str
    payload: Dict[str, Any]


def load_orders(path: Path) -> Dict[str, Order]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return {order_id: Order(id=order_id, payload=data) for order_id, data in raw.items()}


def get_order(orders: Dict[str, Order], order_id: str) -> Optional[Order]:
    return orders.get(order_id)


def format_order_status(order: Order) -> str:
    data = order.payload
    status = data.get("status")

    if status == "in_transit":
        parts = [f"Заказ {order.id} в пути."]
        carrier = data.get("carrier")
        eta_days = data.get("eta_days")
        if carrier:
            parts.append(f"Служба доставки: {carrier}.")
        if eta_days is not None:
            parts.append(f"Ориентировочный срок доставки: {eta_days} дн.")
        return " ".join(parts)

    if status == "delivered":
        delivered_at = data.get("delivered_at")
        if delivered_at:
            return f"Заказ {order.id} доставлен {delivered_at}."
        return f"Заказ {order.id} уже доставлен."

    if status == "processing":
        note = data.get("note", "Заказ в обработке.")
        return f"Заказ {order.id} в обработке. {note}"

    return f"Заказ {order.id}: статус {status or 'неизвестен'}."


def build_order_context(order: Order) -> str:
    """
    Текстовый контекст для LLM, чтобы она знала про заказ в последующих вопросах.
    """
    base = format_order_status(order)
    return (
        "Информация о заказе клиента:\n"
        f"{base}\n\n"
        f"Структура заказа (JSON):\n{json.dumps(order.payload, ensure_ascii=False)}"
    )
