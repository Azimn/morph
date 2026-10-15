"""External declarative genome, dynamic imports, and accountable lifecycle."""
from __future__ import annotations

from importlib import import_module, resources
import json


class ArchitecturalMorphogenEngine:
    def __init__(self):
        # Metadata only. No concrete organ or base class is imported at boot.
        self.catalog = json.loads(resources.files("morph_engine.genome")
                                  .joinpath("catalog.json").read_text())
        self.by_id = {item["id"]: item for item in self.catalog}

    def instantiate(self, organ_id: str, turn: int, snapshot: dict | None = None):
        # Never import a path supplied by an input event or snapshot.
        spec = self.by_id[organ_id]
        cls = import_module(f"morph_engine.genome.{spec['module']}").OrganImpl
        organ = cls(turn)
        if snapshot is not None:
            organ.born = snapshot["born"]
            organ.last_used = snapshot["last_used"]
            organ.state = snapshot["state"]
        return organ

    def prune(self, msv, organs: dict, audit) -> list[dict]:
        events = []
        for organ_id in sorted(list(organs)):
            spec = self.by_id[organ_id]
            organ = organs[organ_id]
            reason = None
            if msv.current_turn - organ.last_used > spec["dormant_turns"]:
                reason = "inactivity"
            elif msv.reserve < spec["tax"]:
                reason = "unaffordable"
            if reason:
                # Content is deleted, not hidden in a kernel archive for resurrection.
                del organs[organ_id]
                audit.append("atrophy", msv.current_turn,
                             {"organ": organ_id, "reason": reason, "born": organ.born})
                events.append({"kind": "atrophy", "organ": organ_id, "reason": reason})
            else:
                msv.reserve = round(msv.reserve - spec["tax"], 10)
                audit.append("maintenance", msv.current_turn,
                             {"organ": organ_id, "charged": spec["tax"]})
        return events

    def grow(self, msv, organs: dict, audit) -> list[dict]:
        events = []
        for spec in self.catalog:
            organ_id, channel = spec["id"], spec["channel"]
            if organ_id in organs or msv.gradients[channel] < spec["threshold"]:
                continue
            if msv.reserve < spec["compile_cost"] + spec["tax"]:
                continue
            trigger = msv.trigger_refs.get(channel)
            if not trigger:
                continue
            # Instantiate before committing accounting or mount, so failure cannot
            # leave a receipt claiming a structure that did not get created.
            organ = self.instantiate(organ_id, msv.current_turn)
            receipt = {"organ": organ_id, "gradient": channel,
                       "value": msv.gradients[channel], "threshold": spec["threshold"],
                       "trigger": trigger, "compile_cost": spec["compile_cost"],
                       "tax": spec["tax"], "template": spec["module"]}
            digest = audit.append("genesis", msv.current_turn, receipt)
            organs[organ_id] = organ
            msv.reserve = round(msv.reserve - spec["compile_cost"], 10)
            msv.gradients[channel] = 0.0
            msv.trigger_refs.pop(channel, None)
            events.append({"kind": "genesis", "organ": organ_id, "receipt": digest})
        return events
