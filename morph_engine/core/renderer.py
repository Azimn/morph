"""Deterministic first-person verbalizer; no model calls or NLI claim."""
from __future__ import annotations


class StrictRenderer:
    def __init__(self, style: str = "concise"):
        if style not in ("concise", "plain"):
            raise ValueError("Unknown renderer style")
        self.style = style

    def render(self, experience: dict) -> str:
        # Never render arbitrary payload text as an authoritative self-claim.
        sentences = []
        for item in experience.get("probes", []):
            if item["outcome"] == "UNASSESSABLE":
                sentences.append("I cannot assess that capacity with the evidence I have.")
        if "recalled" in experience:
            sentences.append("I found a stored observation." if experience["recalled"]
                             else "I do not have that observation stored.")
        if "macro" in experience:
            sentences.append("I can reuse the steps I learned." if experience["macro"]
                             else "I need to work through those steps again.")
        if "selected" in experience:
            sentences.append("I have chosen work that fits my current limits.")
        if "partner_known" in experience:
            sentences.append("I have a separate record for this partner.")
        if "trace_found" in experience:
            sentences.append("I can trace that choice." if experience["trace_found"]
                             else "I do not have a trace for that choice.")
        if "goals" in experience:
            sentences.append("I have commitments recorded." if experience["goals"]
                             else "I have no active commitments recorded.")
        if not sentences:
            sentences.append("I can work with what is available in this turn.")
        return (" " if self.style == "concise" else "\n").join(sentences)
