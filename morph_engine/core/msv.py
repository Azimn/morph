"""Bounded, non-episodic kernel bookkeeping and engineer-only audit events."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any

CHANNELS = ("retrieval_loss", "deliberation_tax", "boundary_drop",
            "resource_collision", "social_variance", "epistemic_fog")


class EvidentialOutcome(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNASSESSABLE = "UNASSESSABLE"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def finite(value: Any, name: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


class AuditLog:
    """Append-only by API; hash chained, not signed or externally authenticated.

    Engineer evidence lives outside subject state. Organs cannot replay this log.
    A malicious party able to replace the whole chain can recompute its hashes.
    """
    def __init__(self, events: list[dict] | None = None):
        self._events = json.loads(canonical(events or []))
        self.verify()

    @property
    def events(self) -> list[dict]:
        return json.loads(canonical(self._events))

    def append(self, kind: str, turn: int, payload: dict) -> str:
        body = {"sequence": len(self._events), "kind": kind, "turn": turn,
                "payload": json.loads(canonical(payload)),
                "previous": self._events[-1]["hash"] if self._events else "0" * 64}
        digest = hashlib.sha256(canonical(body)).hexdigest()
        self._events.append(dict(body, hash=digest))
        return digest

    def verify(self) -> None:
        previous = "0" * 64
        for index, item in enumerate(self._events):
            body = {k: v for k, v in item.items() if k != "hash"}
            if (body.get("sequence") != index or body.get("previous") != previous
                    or hashlib.sha256(canonical(body)).hexdigest() != item.get("hash")):
                raise ValueError("Audit chain integrity failure")
            previous = item["hash"]


@dataclass
class MinimalStateVector:
    seed_id: str
    current_turn: int = 0
    session: int = 0
    budget_per_turn: float = 1.0
    reserve: float = 5.0
    reserve_cap: float = 10.0
    scratchpad: dict = field(default_factory=dict)
    gradients: dict = field(default_factory=lambda: dict.fromkeys(CHANNELS, 0.0))
    # Only one bounded, content-free trigger receipt per channel, no past text.
    trigger_refs: dict = field(default_factory=dict)
    now: float = 0.0
