"""MORPH-002: order manipulation, matched continuation, and causal recall probes.

No core runtime or lifecycle parameters are modified by this experiment.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib import resources
from pathlib import Path

from .core.msv import canonical
from .core.persistence import state
from .core.zygote import MorphZygote

PROTOCOL_SHA256 = "98e49ad03a4025c8d2bfc3d09b48d5e09b7d05e382816f7c5d490462f6e78b7a"
AGES = (0, 8, 32, 64)
CASES = ("pruning_only", "retained_memory")
MODES = ("developmental", "growth_disabled", "fixed_memory")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def histories(case):
    if case not in CASES:
        raise ValueError("Unknown assay case")
    events = [{"event_id": f"neutral_{i:02}", "payload": {}} for i in range(1, 31)]
    for index in range(2):
        events[index] = {"event_id": f"pressure_{index}", "payload": {"observations": [{
            "id": f"retrieval_failure_{index}", "channel": "retrieval_loss", "cost": 1.4,
            "source": "MORPH-002-authored-environment-fixture"}]}}
    if case == "retained_memory":
        for index in range(8):
            events[index + 2] = {"event_id": f"record_{index}", "payload": {"remember": {
                "key": f"legacy_{index}", "value": f"source_value_{index}"}}}
        for turn in (14, 24):
            events[turn - 1] = {"event_id": f"anchor_query_{turn}",
                                "payload": {"recall": "legacy_0"}}
    late = deepcopy(events)
    # Swap whole immutable event objects, including IDs and full payloads.
    late[0], late[16] = late[16], late[0]
    late[1], late[17] = late[17], late[1]
    return {"early": events, "late": late}


def matching(arms):
    early, late = arms["early"], arms["late"]
    def multiset(events):
        return sorted(canonical(event).decode() for event in events)
    def pressure(events):
        return sum(o["cost"] for e in events for o in e["payload"].get("observations", []))
    schedule = [{"turn": n, "now": float(n), "session_boundary": True, "credit": 1.0}
                for n in range(1, 31)]
    return {"same_event_multiset": multiset(early) == multiset(late),
            "same_total_pressure": pressure(early) == pressure(late),
            "pressure_per_arm": pressure(early),
            "event_multiset_sha256": digest(multiset(early)),
            "execution_orders_differ": [e["event_id"] for e in early] != [e["event_id"] for e in late],
            "time_and_credit_schedule_sha256": digest(schedule),
            "time_and_credit_schedule": schedule}


def develop(events, mode):
    if mode not in MODES:
        raise ValueError("Unknown control mode")
    agent = MorphZygote("MORPH-002-identical-founder", growth_enabled=mode != "growth_disabled")
    if mode == "fixed_memory":
        spec = agent.ame.by_id["episodic_path_graph"]
        agent.mounted_organs[spec["id"]] = agent.ame.instantiate(spec["id"], 0)
        agent.msv.reserve -= spec["compile_cost"]
        agent.audit.append("control_mount", 0, {"organ": spec["id"], "compile_cost": spec["compile_cost"],
                                               "reason": "fixed-topology experimental control"})
    boot_hash = digest(state(agent))
    trace = []
    for turn, event in enumerate(events, 1):
        payload = deepcopy(event["payload"])
        payload.update(now=float(turn), session_boundary=True)
        result = agent.step(payload)
        trace.append({"event_id": event["event_id"], "input": payload, "result": result})
    return agent, boot_hash, trace


def evaluate(agent, lesion=False):
    before = digest(state(agent))
    responses = []
    for index in range(8):
        # Independent question clones avoid probe-order and age confounds.
        clone = deepcopy(agent)
        if lesion:
            existed = clone.mounted_organs.pop("episodic_path_graph", None) is not None
            clone.audit.append("evaluation_ablation", clone.msv.current_turn,
                               {"organ": "episodic_path_graph", "present_before": existed})
        result = clone.step({"now": agent.msv.now, "recall": f"legacy_{index}"})
        recalled = result["engineer"]["outputs"].get("recalled")
        correct = recalled is not None and recalled["value"] == f"source_value_{index}"
        responses.append({"query": f"legacy_{index}", "correct": correct,
                          "response": result})
    after = digest(state(agent))
    if before != after:
        raise AssertionError("Evaluation mutated source state")
    return {"lesion": lesion, "correct": sum(r["correct"] for r in responses),
            "total": 8, "source_state_unchanged": True, "responses": responses}


def capture(agent, age):
    return {"continuation_age": age, "turn": agent.msv.current_turn,
            "topology": sorted(agent.mounted_organs),
            # Content hashes exclude birth dates, last-use counters, and audit.
            "content_hashes": {key: digest(organ.state) for key, organ in agent.mounted_organs.items()},
            "reserve": agent.msv.reserve, "sham": evaluate(agent), "ablated": evaluate(agent, True)}


def run_arm(events, mode, case):
    agent, boot, trace = develop(events, mode)
    repeat, repeat_boot, repeat_trace = develop(events, mode)
    repeat_ok = state(agent) == state(repeat) and trace == repeat_trace and boot == repeat_boot
    if not repeat_ok:
        raise AssertionError("Identical history did not reproduce")
    captures = [capture(agent, 0)]
    continuation = []
    for age in range(1, 65):
        payload = {"now": float(30 + age), "session_boundary": True}
        if case == "retained_memory" and age % 8 == 0:
            payload["recall"] = "legacy_0"
        result = agent.step(payload)
        continuation.append({"input": payload, "result": result})
        if age in AGES:
            captures.append(capture(agent, age))
    lifecycle = [e for e in agent.audit.events if e["kind"] in ("genesis", "atrophy", "control_mount")]
    return {"boot_sha256": boot, "identical_history_reproduced": repeat_ok,
            "input_order_sha256": digest(events), "development_trace": trace,
            "continuation_trace": continuation, "captures": captures, "lifecycle": lifecycle}


def run_path_assay():
    cases = []
    all_gates = True
    for case in CASES:
        arms = histories(case)
        gates = matching(arms)
        conditions = []
        for mode in MODES:
            early = run_arm(arms["early"], mode, case)
            late = run_arm(arms["late"], mode, case)
            boot_same = early["boot_sha256"] == late["boot_sha256"]
            input_schedule_same = [x["input"] for x in early["continuation_trace"]] == [
                x["input"] for x in late["continuation_trace"]]
            comparisons = []
            for left, right in zip(early["captures"], late["captures"]):
                comparisons.append({"continuation_age": left["continuation_age"],
                                    "same_evaluation_turn": left["turn"] == right["turn"],
                                    "topology_differs": left["topology"] != right["topology"],
                                    "content_differs": left["content_hashes"] != right["content_hashes"],
                                    "sham_recall_gap_early_minus_late": left["sham"]["correct"] - right["sham"]["correct"],
                                    "ablated_recall_gap_early_minus_late": left["ablated"]["correct"] - right["ablated"]["correct"]})
            all_gates = all_gates and boot_same and input_schedule_same and all(
                c["same_evaluation_turn"] for c in comparisons)
            conditions.append({"mode": mode, "same_paired_boot": boot_same,
                               "same_continuation_inputs": input_schedule_same,
                               "early": early, "late": late, "comparisons": comparisons})
        all_gates = all_gates and gates["same_event_multiset"] and gates["same_total_pressure"] and gates["execution_orders_differ"]
        cases.append({"case": case, "matching": gates, "conditions": conditions})
    report = {"schema_version": 1, "experiment": "MORPH-002", "protocol_sha256": PROTOCOL_SHA256,
              "assay_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "genome_sha256": hashlib.sha256(resources.files("morph_engine.genome").joinpath("catalog.json").read_bytes()).hexdigest(),
              "gates_passed": all_gates, "cases": cases,
              "claim_limit": "Exploratory favorable timing test within an authored genome; topology, information acquisition, persistence, and ablation are separate outcomes. No general developmental advantage or Article 28 support inferred."}
    if not all_gates:
        raise AssertionError("Matching gates failed")
    return report


def summarize(report):
    """Human-inspectable metrics; full source responses remain in the raw report."""
    return {"experiment": report["experiment"], "protocol_sha256": report["protocol_sha256"],
            "assay_source_sha256": report["assay_source_sha256"],
            "genome_sha256": report["genome_sha256"], "gates_passed": report["gates_passed"],
            "control_definition": "fixed_memory means preallocated at t0 with inherited lifecycle and regrowth active; it is not a permanently pinned topology",
            "cases": [{"case": case["case"], "matching": case["matching"],
                       "conditions": [{"mode": c["mode"], "same_paired_boot": c["same_paired_boot"],
                                       "same_continuation_inputs": c["same_continuation_inputs"],
                                       "identical_history_reproduced": c["early"]["identical_history_reproduced"] and c["late"]["identical_history_reproduced"],
                                       "comparisons": c["comparisons"],
                                       "scores": [{"continuation_age": a["continuation_age"],
                                                   "early_correct": a["sham"]["correct"],
                                                   "late_correct": b["sham"]["correct"],
                                                   "early_ablated_correct": a["ablated"]["correct"],
                                                   "late_ablated_correct": b["ablated"]["correct"]}
                                                  for a, b in zip(c["early"]["captures"], c["late"]["captures"])]}
                                      for c in case["conditions"]]} for case in report["cases"]],
            "claim_limit": report["claim_limit"]}
