"""Traces: a complete, replayable record of what the agent saw and did.

If you cannot see why an agent failed, you cannot fix it. Every model turn,
tool call, permission decision, and test run lands here as one event, and the
whole run serialises to a single JSON file the web viewer reads directly.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Event:
    step: int
    kind: str  # thought | tool | denied | note | final
    at_ms: int
    tool: str = ""
    input: dict = field(default_factory=dict)
    output: str = ""
    is_error: bool = False
    duration_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class Trace:
    task: str
    provider: str
    model: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    started_at: float = field(default_factory=time.time)
    events: list[Event] = field(default_factory=list)
    outcome: str = "running"
    summary: str = ""
    diff: str = ""
    grading: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._t0 = time.monotonic()

    def add(self, kind: str, step: int, **fields) -> Event:
        event = Event(step=step, kind=kind, at_ms=int((time.monotonic() - self._t0) * 1000), **fields)
        self.events.append(event)
        return event

    @property
    def tokens(self) -> tuple[int, int]:
        return sum(e.tokens_in for e in self.events), sum(e.tokens_out for e in self.events)

    @property
    def wall_ms(self) -> int:
        return self.events[-1].at_ms if self.events else 0

    def to_dict(self) -> dict:
        data = asdict(self)
        tin, tout = self.tokens
        data["tokens_in"], data["tokens_out"], data["wall_ms"] = tin, tout, self.wall_ms
        data["steps"] = max((e.step for e in self.events), default=0)
        return data

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path
