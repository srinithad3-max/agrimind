"""
Blackboard: the shared memory every agent reads from and writes to.

Agents never call each other directly. They publish facts to topics on the
blackboard (e.g. "weather.forecast", "disease.diagnosis") and send messages
to each other through it. The orchestrator streams every message to the
dashboard so the cooperation is visible live.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any


class Blackboard:
    def __init__(self, context: dict):
        self.context = context            # farm profile + inputs
        self.facts: dict[str, Any] = {}   # topic -> value
        self.events: deque = deque()      # pending events to stream
        self.log: list[dict] = []         # full message history
        self.t0 = time.time()

    # ---- facts -------------------------------------------------------------
    def publish(self, topic: str, value: Any, by: str):
        self.facts[topic] = value
        self._emit(dict(type="fact", topic=topic, by=by))

    def get(self, topic: str, default=None):
        return self.facts.get(topic, default)

    # ---- messages ----------------------------------------------------------
    def message(self, sender: str, text: str, to: str = "all", level: str = "info"):
        evt = dict(type="message", sender=sender, to=to, text=text, level=level,
                   t=round(time.time() - self.t0, 2))
        self.log.append(evt)
        self._emit(evt)

    def _emit(self, evt: dict):
        self.events.append(evt)

    def drain(self):
        while self.events:
            yield self.events.popleft()
