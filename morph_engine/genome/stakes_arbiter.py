"""Budget-constrained task selection with a clampable caution scalar."""
from .base_organ import Organ


class OrganImpl(Organ):
    def __init__(self, turn):
        super().__init__(turn)
        self.state = {"caution": 0.65, "workspace": 2}

    def intervene(self, key, value):
        if key == "caution" and (isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= 1):
            raise ValueError("Caution must be in [0, 1]")
        if key == "workspace" and (type(value) is not int or value < 1):
            raise ValueError("Workspace must be a positive integer")
        return super().intervene(key, value)

    def process(self, data, turn, now, budget):
        tasks = data.get("tasks", [])
        if not tasks:
            return {}
        self.used(turn)
        caution = self.state["caution"]
        learned = data.get("_learned_policy")
        applied = {}
        effective = []
        for task in tasks:
            risk = task["risk"]
            if learned is not None and task.get("affordance") == learned["domain"]:
                risk = max(risk, 1.0 - learned["reliability"])
                applied[task["id"]] = {"domain": learned["domain"], "base_risk": task["risk"],
                                        "effective_risk": risk, "reliability": learned["reliability"]}
            effective.append(dict(task, risk=risk))
        ranked = sorted(effective, key=lambda t: (-(t["value"] - caution * t["risk"] * 1.5 - t["cost"]), t["id"]))
        chosen, deferred, spent = [], [], 0.0
        for task in ranked:
            utility = task["value"] - caution * task["risk"] * 1.5 - task["cost"]
            if utility > 0 and len(chosen) < self.state["workspace"] and spent + task["cost"] <= budget + 1e-12:
                chosen.append(task["id"])
                spent += task["cost"]
            else:
                deferred.append(task["id"])
        result = {"selected": chosen, "deferred": deferred, "task_cost": spent, "caution": caution}
        if applied:
            result["applied_memory_risk"] = applied
        return result
