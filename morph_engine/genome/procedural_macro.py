"""Repeated verified pure trajectories become executable sandboxed macros."""
from .base_organ import Organ
import json
import math


def execute(steps, value):
    for operation, operand in steps:
        if operation == "add":
            value += operand
        elif operation == "multiply":
            value *= operand
        else:
            raise ValueError("Unsupported pure action")
        if not math.isfinite(value):
            raise ValueError("Macro arithmetic overflow")
    return value


class OrganImpl(Organ):
    def __init__(self, turn):
        super().__init__(turn)
        self.state = {"counts": {}, "macros": {}}

    def preflight(self, request):
        steps = self.state["macros"].get(request["id"])
        if steps is not None and not request.get("perturbed", False):
            execute(steps, request["input"])

    def process(self, data, turn, now, budget):
        result = {}
        if "workflow" in data:
            workflow = data["workflow"]
            # Exact action sequence identity prevents signature alias poisoning.
            signature = json.dumps(workflow["steps"], separators=(",", ":"))
            count = self.state["counts"].get(signature, 0)
            if execute(workflow["steps"], workflow["input"]) == workflow["expected"]:
                count += 1
                self.state["counts"][signature] = count
                if count >= 5:
                    self.state["macros"][workflow["id"]] = workflow["steps"]
                self.used(turn)
        if "run_macro" in data:
            request = data["run_macro"]
            steps = self.state["macros"].get(request["id"])
            if steps is not None and not request.get("perturbed", False):
                result = {"macro": True, "result": execute(steps, request["input"]),
                          "planning_units": 0}
                self.used(turn)
            else:
                result = {"macro": False, "result": None, "planning_units": None}
        return result
