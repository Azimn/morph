"""Prospective decision traces, not retrospective fabricated rationales."""
from .base_organ import Organ


class OrganImpl(Organ):
    def __init__(self, turn):
        super().__init__(turn)
        self.state = {"traces": {}, "tensions": [], "calibration": []}

    def observe(self, decision_id, decision, turn):
        self.state["traces"][decision_id] = decision
        self.used(turn)

    def process(self, data, turn, now, budget):
        result = {}
        if "audit_decision" in data:
            self.used(turn)
            trace = self.state["traces"].get(data["audit_decision"])
            result.update(trace_found=trace is not None, decision_trace=trace)
        if "conflict" in data:
            self.state["tensions"].append(data["conflict"])
            self.used(turn)
        if "resolve_conflict" in data and data["resolve_conflict"] in self.state["tensions"]:
            self.state["tensions"].remove(data["resolve_conflict"])
            self.used(turn)
        if "confidence_outcome" in data:
            item = data["confidence_outcome"]
            score = (item["confidence"] - float(item["success"])) ** 2
            self.state["calibration"].append(score)
            result["brier_score"] = score
            self.used(turn)
        return result
