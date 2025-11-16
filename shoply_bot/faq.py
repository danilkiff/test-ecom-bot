# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class FAQItem:
    question: str
    answer: str


def load_faq(path: Path) -> List[FAQItem]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [FAQItem(question=item["q"], answer=item["a"]) for item in raw]


_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _normalize(text: str):
    return set(_WORD_RE.findall(text.lower()))


def find_top_faq_matches(
        user_question: str,
        faq_items: List[FAQItem],
        k: int = 3,
        min_overlap: int = 1,
) -> List[FAQItem]:
    """
    Игрушечный retrieval по пересечению токенов.
    """
    q_tokens = _normalize(user_question)
    scored = []

    for item in faq_items:
        score = len(q_tokens & _normalize(item.question))
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [item for score, item in scored[:k] if score >= min_overlap]
    return result


def build_faq_context(matches: List[FAQItem]) -> str:
    if not matches:
        return (
            "Подходящего вопроса в FAQ не найдено. "
            "Ответь, что у тебя нет достаточной информации и предложи обратиться к оператору."
        )

    blocks = []
    for item in matches:
        blocks.append(f"Вопрос: {item.question}\nОтвет: {item.answer}")
    return "Выдержка из FAQ:\n\n" + "\n\n".join(blocks)
