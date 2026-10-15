"""Contract loaded only when the first organ differentiates."""
from __future__ import annotations


class Organ:
    def __init__(self, turn: int, state: dict | None = None):
        self.born = turn
        self.last_used = turn
        self.state = {} if state is None else state

    def used(self, turn: int) -> None:
        self.last_used = turn

    def process(self, data: dict, turn: int, now: float, budget: float) -> dict:
        return {}

    def snapshot(self) -> dict:
        return {"born": self.born, "last_used": self.last_used, "state": self.state}

    def intervene(self, key: str, value):
        if key not in self.state:
            raise KeyError(key)
        old = self.state[key]
        if type(value) is not type(old):
            raise ValueError("Clamp must preserve state type")
        self.state[key] = value
        return old
