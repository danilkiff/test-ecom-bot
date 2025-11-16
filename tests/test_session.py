# SPDX-License-Identifier: CC0-1.0

from pathlib import Path
from shoply_bot.session import SessionState


def test_usage_totals_accumulate(tmp_path: Path):
    log_path = tmp_path / "session.jsonl"
    state = SessionState(
        session_id="test",
        brand="Shoply",
        model="gpt-4o-mini",
        log_path=log_path,
    )

    state.log_usage_step({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    state.log_usage_step({"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5})

    assert state.usage_totals.prompt_tokens == 13
    assert state.usage_totals.completion_tokens == 7
    assert state.usage_totals.total_tokens == 20
