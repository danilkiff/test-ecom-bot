# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

from typing import Dict

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

SYSTEM_TEMPLATE = """
Ты консольный бот поддержки магазина {brand}.
Правила:
- Отвечай кратко, вежливо, по делу.
- Используй ТОЛЬКО переданный контекст (FAQ и информацию о заказе).
- Не придумывай факты вне этого контекста.
- Если информации недостаточно, честно скажи об этом и предложи обратиться к оператору.
- Отвечай на русском языке.
""".strip()


def build_chain(model_name: str, brand: str):
    chat = ChatOpenAI(
        model=model_name,
        temperature=0,
        timeout=15,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE.format(brand=brand)),
        ("system", "{context}"),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])

    chain = prompt | chat

    store: Dict[str, InMemoryChatMessageHistory] = {}

    def get_history(session_id: str):
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_history,
        input_messages_key="question",
        history_messages_key="history",
    )

    return chain_with_history, get_history
