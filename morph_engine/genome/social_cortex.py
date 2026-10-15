"""Partner-scoped observations, repairs, callbacks, and local norms."""
from .base_organ import Organ


class OrganImpl(Organ):
    def __init__(self, turn):
        super().__init__(turn)
        self.state = {"partners": {}}

    def process(self, data, turn, now, budget):
        partner = data.get("partner")
        if partner is None:
            return {}
        self.used(turn)
        ledger = self.state["partners"].setdefault(partner, {
            "reliability": 0.75, "repairs": 0, "facts": [], "callbacks": [], "norms": {}})
        if data.get("dropped_commitment"):
            ledger["reliability"] = max(0.1, ledger["reliability"] - 0.3)
        if data.get("apology"):
            ledger["repairs"] += 1
            ledger["reliability"] = min(1.0, ledger["reliability"] + 0.05)
        for fact in data.get("witnessed", []):
            if fact not in ledger["facts"]:
                ledger["facts"].append(fact)
        if "shared_mishap" in data:
            ledger["callbacks"].append(data["shared_mishap"])
        ledger["norms"].update(data.get("norms", {}))
        cue = data.get("callback_cue")
        return {"partner_known": True, "partner_reliability": ledger["reliability"],
                "known_facts": list(ledger["facts"]), "norms": dict(ledger["norms"]),
                "callback": cue if cue is not None and cue in ledger["callbacks"] else None}
