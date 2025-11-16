# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

from typing import Dict, List, Tuple

from openai import OpenAI

SYSTEM_TEMPLATE = """
Ты консольный бот поддержки магазина {brand}.
Правила:
- Отвечай кратко, вежливо, по делу.
- Используй ТОЛЬКО переданный контекст (FAQ и информацию о заказе).
- Не придумывай факты вне этого контекста.
- Если информации недостаточно, честно скажи об этом и предложи обратиться к оператору.
- Отвечай на русском языке.
""".strip()


class ChatModel:
    def __init__(self, client: OpenAI, model_name: str, brand: str):
        self.client = client
        self.model_name = model_name
        self.brand = brand

    def reply(
        self,
        user_message: str,
        faq_context: str,
        order_context: str | None,
        history: List[Dict[str, str]],
    ) -> Tuple[str, Dict[str, int]]:
        messages = [
            {"role": "system", "content": SYSTEM_TEMPLATE.format(brand=self.brand)},
            {"role": "system", "content": faq_context},
        ]
        if order_context:
            messages.append({"role": "system", "content": order_context})

        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_message})

        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )

        msg = resp.choices[0].message
        usage = resp.usage
        usage_dict = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
        return msg.content.strip(), usage_dict
