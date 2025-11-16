# SPDX-License-Identifier: CC0-1.0

from shoply_bot.faq import FAQItem, find_top_faq_matches, build_faq_context


def test_find_top_faq_matches_basic_overlap():
    faq = [
        FAQItem("Как оформить возврат?", "Возврат в течение 14 дней."),
        FAQItem("Сколько идёт доставка?", "2–5 дней."),
    ]

    matches = find_top_faq_matches("сколько будет идти моя доставка", faq, k=1)
    assert len(matches) == 1
    assert "доставка" in matches[0].question.lower()


def test_build_faq_context_empty():
    ctx = build_faq_context([])
    assert "не найдено" in ctx.lower()


def test_build_faq_context_non_empty():
    faq = [FAQItem("Q1", "A1")]
    ctx = build_faq_context(faq)
    assert "Q1" in ctx
    assert "A1" in ctx
