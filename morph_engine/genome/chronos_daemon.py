"""Persisted deadline queue. Host must invoke tick; no hidden daemon thread."""
from .base_organ import Organ


class OrganImpl(Organ):
    def __init__(self, turn):
        super().__init__(turn)
        self.state = {"goals": {}, "last_tick": 0.0}

    def process(self, data, turn, now, budget):
        if "new_goal" in data:
            goal = data["new_goal"]
            if goal["id"] in self.state["goals"]:
                raise ValueError("Goal identifiers cannot be reused")
            self.state["goals"][goal["id"]] = {"due": goal["due"], "status": "ACTIVE"}
            self.used(turn)
        if "complete_goal" in data and data["complete_goal"] in self.state["goals"]:
            self.state["goals"][data["complete_goal"]]["status"] = "COMPLETED"
            self.used(turn)
        return {"goals": sorted(k for k, v in self.state["goals"].items()
                                if v["status"] == "ACTIVE")}

    def tick(self, now, budget, turn):
        if now < self.state["last_tick"]:
            raise ValueError("Clock cannot move backwards")
        self.state["last_tick"] = now
        due = []
        for goal_id, goal in sorted(self.state["goals"].items(), key=lambda x: (x[1]["due"], x[0])):
            if goal["status"] == "ACTIVE" and goal["due"] <= now and budget + 1e-12 >= 0.1:
                budget = round(budget - 0.1, 10)
                goal["status"] = "DUE_EMITTED"
                due.append(goal_id)
                self.used(turn)
        return {"due": due, "spent": round(len(due) * 0.1, 10)}
