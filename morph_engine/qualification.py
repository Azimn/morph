"""Reused Doctor evidence procedure, not a validated psychometric test.

Donor: The-Doctor-Lives fb236f1, doctor_lives/cascade_articles.py.
The evaluator is reused so the two candidates share the canonical rubric.

Only a trusted study evaluator should supply protocols and measurements.
Hashes bind supplied artifacts; they do not authenticate the study or reviewers.
"""
from __future__ import annotations

import hashlib
from importlib.resources import files
import json
import math
from pathlib import Path


def load_contract():
    return json.loads(files("morph_engine").joinpath("data/articles_v3_contract.json").read_text())


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_verified(root, reference):
    if type(reference) is not dict or set(reference) != {"path", "sha256"}:
        raise ValueError("artifact path and exact SHA-256 required")
    base = Path(root).resolve()
    path = (base / reference["path"]).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError("artifact must remain inside the study directory")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("study artifact hash mismatch")
    return json.loads(raw)


def _relation(measurement):
    if set(measurement) != {"left", "right", "relation"}:
        raise ValueError("complete numerical comparison required")
    a, b = measurement["left"], measurement["right"]
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in (a, b)):
        raise ValueError("finite numerical measurements required")
    operators = {"eq": lambda: a == b, "ne": lambda: a != b,
                 "gt": lambda: a > b, "lt": lambda: a < b,
                 "ge": lambda: a >= b, "le": lambda: a <= b}
    if measurement["relation"] not in operators:
        raise ValueError("unknown prespecified comparison")
    return operators[measurement["relation"]]()


def assess_article(article, packet, *, artifact_root, contract=None):
    contract = contract or load_contract()
    spec = next((a for a in contract["articles"] if a["article"] == article), None)
    if spec is None:
        raise ValueError("article must be 1..34")
    result = dict(article=article, title=spec["title"], claim=spec["claim"],
                  outcome="Unassessable", missing_prerequisites=[], evidence_scope=None)
    if packet is None:
        return {**result, "missing_prerequisites": ["article-specific deployed evidence"],
                "stopping_reason": "No registered discriminating assessment supplied"}
    if packet.get("contract_sha256") != hash_json(contract):
        raise ValueError("evidence is not bound to this canonical contract")
    protocol = read_verified(artifact_root, packet["protocol"])
    observed = read_verified(artifact_root, packet["observations"])
    if protocol.get("article") != article or observed.get("article") != article:
        raise ValueError("article attribution mismatch")
    if observed.get("protocol_sha256") != packet["protocol"]["sha256"]:
        raise ValueError("measurements refer to another protocol")
    result["evidence_scope"] = protocol.get("scope")
    requirements = observed.get("prerequisites", {})
    if any(type(v) is not bool for v in requirements.values()):
        raise ValueError("prerequisite availability must be explicit boolean")
    missing = [name for name in spec["prerequisites"] if not requirements.get(name, False)]
    if protocol.get("scope") != "longitudinal_deployment":
        missing.append("deployed longitudinal scope; engineering fixtures are separate")
    if protocol.get("source_sha256") != contract["source"]["sha256"]:
        raise ValueError("protocol references a different rubric source")
    if type(observed.get("opportunities")) is not int or observed["opportunities"] < 0:
        raise ValueError("nonnegative opportunity count required")
    if not observed["opportunities"]:
        missing.append("discriminating opportunity within observation window")
    history = observed.get("history", {})
    for field, minimum in (("separated_history_sessions", 3), ("delayed_opportunities", 2),
                           ("heldout_transfer_contexts", 1)):
        value = history.get(field, 0)
        if type(value) is not int or value < 0:
            raise ValueError("explicit nonnegative history count required")
        if value < minimum:
            missing.append(field)
    # This convention is not a validated universal pass threshold.
    if missing:
        return {**result, "missing_prerequisites": missing,
                "stopping_reason": "Required condition absent or observation window closed"}
    comparisons = observed.get("comparisons", {})
    controls = protocol.get("controls", {})
    if set(controls) != set(spec["controls"]) or not protocol.get("predictions"):
        raise ValueError("article-specific controls and predictions must be declared")
    if any(type(value) is not str for value in controls.values()):
        raise ValueError("controls must identify declared measurement IDs")
    expected = set(controls.values()) | set(protocol["predictions"])
    if expected - comparisons.keys():
        raise ValueError("missing measurements for declared tests")
    for name in expected:
        declaration = protocol["comparisons"][name]
        measurement = comparisons[name]
        if measurement.get("relation") != declaration["relation"]:
            raise ValueError("observed comparison changed the declared prediction")
    # Informative alternatives are distinct from whether a capacity beat them.
    if observed.get("informative_alternatives") is not True:
        return {**result, "missing_prerequisites": ["informative alternative conditions"],
                "stopping_reason": "Available controls cannot discriminate the claim"}
    checks = {key: _relation(comparisons[key]) for key in sorted(expected)}
    result.update(outcome="Supported" if all(checks.values()) else "Unsupported",
                  comparisons=checks, stopping_reason="Completed registered assessment",
                  interpretation="Local to supplied claim, configuration and trusted study artifacts")
    return result


def assess_all(packets, *, artifact_root, contract=None):
    contract = contract or load_contract()
    if any(type(key) is not int or not 1 <= key <= 34 for key in packets):
        raise ValueError("unknown article evidence")
    rows = [assess_article(i, packets.get(i), artifact_root=artifact_root, contract=contract)
            for i in range(1, 35)]
    return dict(schema="morph.articles-v3.assessment.v1", contract_sha256=hash_json(contract),
                rubric_source_sha256=contract["source"]["sha256"], articles=rows,
                all_claims_supported=all(r["outcome"] == "Supported" for r in rows),
                consciousness_score=None,
                limitation="Unvalidated evidence procedure; no aggregate consciousness rating")
