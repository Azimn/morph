"""Zygote runtime, with explicit engineer and subject boundaries."""
from __future__ import annotations

from copy import deepcopy
from .msv import MinimalStateVector, AuditLog, CHANNELS, finite, canonical
from .morphogen import ArchitecturalMorphogenEngine
from .renderer import StrictRenderer


class MorphZygote:
    def __init__(self, seed_id: str, renderer_style: str = "concise", growth_enabled: bool = True):
        if not isinstance(seed_id, str) or not seed_id:
            raise ValueError("seed_id must be nonempty")
        if type(growth_enabled) is not bool:
            raise ValueError("growth_enabled must be boolean")
        self.growth_enabled = growth_enabled
        self.msv = MinimalStateVector(seed_id)
        self.ame = ArchitecturalMorphogenEngine()
        self.renderer = StrictRenderer(renderer_style)
        self.mounted_organs = {}
        self.audit = AuditLog()

    def probe(self, article: int) -> dict:
        if type(article) is not int or not 1 <= article <= 34:
            raise ValueError("Article must be an integer in 1..34")
        required = [s["id"] for s in self.ame.catalog if article in s["articles"]]
        absent = [key for key in required if key not in self.mounted_organs]
        return {"article": article, "outcome": "UNASSESSABLE", "missing": absent,
                "reason": "organ_absent" if absent else "article_protocol_not_supplied"}

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict):
            raise ValueError("Turn input must be an object")
        canonical(data)
        allowed = {"observations", "probes", "now", "session_boundary", "scratchpad", "remember",
                   "recall", "domain_outcome", "domain", "ambiguous_probe", "workflow", "run_macro",
                   "new_goal", "complete_goal", "tasks", "partner", "dropped_commitment", "apology",
                   "witnessed", "shared_mishap", "norms", "callback_cue", "audit_decision", "conflict",
                   "resolve_conflict", "confidence_outcome"}
        if set(data) - allowed:
            raise ValueError(f"Unknown input fields: {sorted(set(data) - allowed)}")
        if not isinstance(data.get("observations", []), list):
            raise ValueError("observations must be a list")
        if not isinstance(data.get("probes", []), list):
            raise ValueError("probes must be a list")
        for observation in data.get("observations", []):
            if not isinstance(observation, dict) or set(observation) != {"id", "channel", "cost", "source"}:
                raise ValueError("Observation requires id, channel, cost, source")
            if observation["channel"] not in CHANNELS:
                raise ValueError("Unknown friction channel")
            for name in ("id", "source"):
                if not isinstance(observation[name], str) or not observation[name]:
                    raise ValueError(f"Observation {name} must be nonempty")
            finite(observation["cost"], "cost")
        for name in ("now",):
            if name in data:
                finite(data[name], name)
        for article in data.get("probes", []):
            if type(article) is not int or not 1 <= article <= 34:
                raise ValueError("Invalid Article")
        for name in ("session_boundary", "ambiguous_probe", "dropped_commitment", "apology"):
            if name in data and type(data[name]) is not bool:
                raise ValueError(f"{name} must be boolean")
        for name in ("recall", "domain", "partner", "complete_goal", "shared_mishap",
                     "callback_cue", "audit_decision", "conflict", "resolve_conflict"):
            if name in data and (not isinstance(data[name], str) or not data[name]):
                raise ValueError(f"{name} must be nonempty text")
        for name in ("scratchpad", "norms"):
            if name in data and not isinstance(data[name], dict):
                raise ValueError(f"{name} must be an object")
        if "witnessed" in data and (not isinstance(data["witnessed"], list) or
                                    any(not isinstance(x, str) for x in data["witnessed"])):
            raise ValueError("witnessed must be a string list")
        if "remember" in data:
            item = data["remember"]
            if not isinstance(item, dict) or set(item) != {"key", "value"} or not isinstance(item["key"], str):
                raise ValueError("remember requires text key and JSON value")
        if "domain_outcome" in data:
            item = data["domain_outcome"]
            if (not isinstance(item, dict) or set(item) != {"domain", "success"}
                    or not isinstance(item["domain"], str) or type(item["success"]) is not bool):
                raise ValueError("domain_outcome requires domain and boolean success")
        if "new_goal" in data:
            goal = data["new_goal"]
            if not isinstance(goal, dict) or set(goal) != {"id", "due"} or not isinstance(goal["id"], str) or not goal["id"]:
                raise ValueError("Goal requires id and due timestamp")
            finite(goal["due"], "due")
        if "confidence_outcome" in data:
            item = data["confidence_outcome"]
            if not isinstance(item, dict) or set(item) != {"confidence", "success"} or type(item["success"]) is not bool:
                raise ValueError("Invalid confidence outcome")
            if finite(item["confidence"], "confidence") > 1:
                raise ValueError("Confidence exceeds 1")
        for name in ("workflow", "run_macro"):
            if name not in data:
                continue
            item = data[name]
            required = {"id", "steps", "input", "expected"} if name == "workflow" else {"id", "input"}
            if not isinstance(item, dict) or not required <= set(item) or set(item) - required - {"perturbed"}:
                raise ValueError("Invalid workflow fields")
            if not isinstance(item["id"], str) or not item["id"]:
                raise ValueError("Workflow id required")
            finite(item["input"], "workflow input", minimum=-1e100)
            if "perturbed" in item and type(item["perturbed"]) is not bool:
                raise ValueError("perturbed must be boolean")
            if name == "workflow":
                finite(item["expected"], "expected", minimum=-1e100)
                if not isinstance(item["steps"], list) or not item["steps"]:
                    raise ValueError("Workflow requires action steps")
                value = item["input"]
                for step in item["steps"]:
                    if not isinstance(step, list) or len(step) != 2 or step[0] not in ("add", "multiply"):
                        raise ValueError("Only add/multiply pure actions allowed")
                    finite(step[1], "operand", minimum=-1e100)
                    value = value + step[1] if step[0] == "add" else value * step[1]
                    finite(value, "workflow result", minimum=-1e100)
        tasks = data.get("tasks", [])
        if not isinstance(tasks, list):
            raise ValueError("tasks must be a list")
        ids = set()
        for task in tasks:
            if not isinstance(task, dict) or set(task) != {"id", "value", "risk", "cost"}:
                raise ValueError("Task requires id, value, risk, cost")
            if not isinstance(task["id"], str) or not task["id"] or task["id"] in ids:
                raise ValueError("Task ids must be unique nonempty text")
            ids.add(task["id"])
            for key in ("value", "risk", "cost"):
                finite(task[key], key)

    def step(self, data: dict) -> dict:
        # Validate everything before advancing time or spending resources.
        self._validate(data)
        data = deepcopy(data)
        now = data.get("now", self.msv.now)
        if now < self.msv.now:
            raise ValueError("Clock cannot move backwards")
        ids = [o["id"] for o in data.get("observations", [])]
        existing = {e["payload"]["id"] for e in self.audit.events if e["kind"] == "friction"}
        if len(ids) != len(set(ids)) or existing.intersection(ids):
            raise ValueError("Duplicate observation id")
        chronos = self.mounted_organs.get("chronos_daemon")
        if chronos and "new_goal" in data and data["new_goal"]["id"] in chronos.state["goals"]:
            raise ValueError("Goal identifiers cannot be reused")
        macro = self.mounted_organs.get("procedural_macro_cortex")
        if macro and "run_macro" in data:
            macro.preflight(data["run_macro"])
        self.msv.current_turn += 1
        self.msv.now = now
        self.msv.scratchpad = deepcopy(data.get("scratchpad", {}))
        if data.get("session_boundary"):
            self.msv.session += 1
        self.msv.reserve = min(self.msv.reserve_cap, self.msv.reserve + self.msv.budget_per_turn)
        lifecycle = self.ame.prune(self.msv, self.mounted_organs, self.audit)
        before = sorted(self.mounted_organs)
        probes = [self.probe(article) for article in data.get("probes", [])]
        for observation in data.get("observations", []):
            spec = next(s for s in self.ame.catalog if s["channel"] == observation["channel"])
            digest = self.audit.append("friction", self.msv.current_turn, observation)
            if spec["id"] not in self.mounted_organs:
                channel = observation["channel"]
                total = self.msv.gradients[channel] + observation["cost"]
                # Saturation prevents unbounded growth from finite but huge inputs.
                self.msv.gradients[channel] = min(total, 1e100)
                self.msv.trigger_refs[channel] = digest
            self.msv.reserve = max(0.0, self.msv.reserve - observation["cost"] * 0.25)
        outputs = {}
        for organ_id, organ in self.mounted_organs.items():
            if organ_id != "metacognitive_audit_mirror":
                outputs.update(organ.process(data, self.msv.current_turn, now, self.msv.budget_per_turn))
        mirror = self.mounted_organs.get("metacognitive_audit_mirror")
        if mirror:
            outputs.update(mirror.process(data, self.msv.current_turn, now, self.msv.budget_per_turn))
            if "selected" in outputs:
                mirror.observe(f"decision_{self.msv.current_turn}", {
                    "selected": list(outputs["selected"]), "deferred": list(outputs["deferred"]),
                    "caution": outputs["caution"], "tasks": deepcopy(data.get("tasks", []))}, self.msv.current_turn)
        self.audit.append("turn", self.msv.current_turn, {
            "mounted": before, "output": deepcopy(outputs), "probes": probes})
        if self.growth_enabled:
            lifecycle.extend(self.ame.grow(self.msv, self.mounted_organs, self.audit))
        experience = dict(outputs, probes=probes)
        # Subject receives first-person prose. This API's separate engineer record
        # must never be passed verbatim as the subject's inner experience.
        return {"subject_text": self.renderer.render(experience), "engineer": deepcopy({
            "turn": self.msv.current_turn, "mounted_before": before,
            "mounted_after": sorted(self.mounted_organs), "outputs": outputs,
            "probes": probes, "lifecycle": lifecycle, "reserve": self.msv.reserve})}

    def tick(self, now: float, budget: float) -> dict:
        now, budget = finite(now, "now"), finite(budget, "budget")
        if now < self.msv.now:
            raise ValueError("Clock cannot move backwards")
        organ = self.mounted_organs.get("chronos_daemon")
        if organ is None:
            return {"status": "UNASSESSABLE", "reason": "organ_absent", "due": [], "spent": 0.0}
        # Budget is both caller-authorized and reserve-limited. No network/tool work.
        result = organ.tick(now, min(budget, self.msv.reserve), self.msv.current_turn)
        self.msv.now = now
        self.msv.reserve = round(self.msv.reserve - result["spent"], 10)
        self.audit.append("tick", self.msv.current_turn, dict(result, now=now, authorized_budget=budget))
        return result

    def intervene(self, organ_id: str, key: str, value):
        if organ_id not in self.mounted_organs:
            raise ValueError("Cannot clamp absent organ")
        if organ_id != "homeostatic_stakes_arbiter":
            raise ValueError("Only arbiter caution/workspace clamps are validated in v0.1")
        canonical(value)
        old = self.mounted_organs[organ_id].intervene(key, value)
        self.audit.append("intervention", self.msv.current_turn,
                          {"organ": organ_id, "key": key, "old": old, "new": value})
        return old
