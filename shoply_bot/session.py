# SPDX-License-Identifier: CC0-1.0

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class UsageTotals:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add_step(self, usage: Dict[str, int]):
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)


@dataclass
class SessionState:
    session_id: str
    brand: str
    model: str
    log_path: Path
    history: List[Dict[str, str]] = field(default_factory=list)
    last_order_context: Optional[str] = None
    usage_totals: UsageTotals = field(default_factory=UsageTotals)

    def log_event(self, role: str, content: str, usage: Dict[str, Any] | None = None, extra: Dict[str, Any] | None = None):
        event = {
            "type": "message",
            "timestamp": datetime.now(UTC).isoformat(),
            "role": role,
            "content": content,
        }
        if usage is not None:
            event["usage"] = usage
        if extra:
            event.update(extra)

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def init_meta(self):
        meta = {
            "type": "meta",
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": self.session_id,
            "brand": self.brand,
            "model": self.model,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    def add_history(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self.history = self.history[-10:]  # ограничиваем длину истории

    def log_usage_step(self, usage: Dict[str, int]):
        self.usage_totals.add_step(usage)

    def log_usage_summary(self):
        summary = {
            "type": "usage_summary",
            "timestamp": datetime.now(UTC).isoformat(),
            "usage": {
                "prompt_tokens": self.usage_totals.prompt_tokens,
                "completion_tokens": self.usage_totals.completion_tokens,
                "total_tokens": self.usage_totals.total_tokens,
            },
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
