"""Small exact-key episodic store and recency-weighted domain policy.

This is not a Bayesian graph, Kalman filter, vector index, or semantic recall.
"""
from .base_organ import Organ


class OrganImpl(Organ):
    def __init__(self, turn):
        super().__init__(turn)
        self.state = {"episodes": {}, "domains": {}, "activation": {}}

    def process(self, data, turn, now, budget):
        for key in list(self.state["activation"]):
            self.state["activation"][key] *= 0.65
            if self.state["activation"][key] < 0.08:
                del self.state["activation"][key]
        if "remember" in data:
            item = data["remember"]
            self.state["episodes"][item["key"]] = {"value": item["value"], "turn": turn}
            self.used(turn)
        result = {}
        if "recall" in data:
            self.used(turn)
            result["recalled"] = self.state["episodes"].get(data["recall"])
        if "domain_outcome" in data:
            outcome = data["domain_outcome"]
            domain = outcome["domain"]
            node = self.state["domains"].setdefault(domain, {"estimate": 0.5, "trajectory": []})
            observation = float(outcome["success"])
            alpha = 0.35 if observation >= node["estimate"] else 0.55
            node["estimate"] = (1 - alpha) * node["estimate"] + alpha * observation
            node["trajectory"].append(outcome["success"])
            self.state["activation"][domain] = 1.0
            self.used(turn)
        domain = data.get("domain")
        if domain in self.state["domains"]:
            self.used(turn)
            estimate = self.state["domains"][domain]["estimate"]
            result["memory_policy"] = {"reliability": estimate, "reserve": 1.5 * (1 - estimate),
                                       "verification": "STRICT" if estimate < 0.55 else "STANDARD"}
        if data.get("ambiguous_probe") and self.state["activation"]:
            self.used(turn)
            result["prime"] = max(self.state["activation"], key=self.state["activation"].get)
        return result
