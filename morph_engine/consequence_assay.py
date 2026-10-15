"""MORPH-003 actual pure-tool outcomes, restart sessions, and causal controls."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .core.msv import canonical
from .core.persistence import load, save, state
from .core.zygote import MorphZygote
from .qualification import assess_all, load_contract

PROTOCOL_SHA256 = "059ebc48c321787d7c9d9111f701ec16c659ffc0debbbfa8475c938359b0656a"
MODES = ("intact", "sham", "memory_lesion", "memory_restored", "coupling_disabled")


def truth(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def execute_tool(tool, text, unreliable):
    """Two real computations; the test environment deliberately supplies a stale fast tool."""
    started = time.perf_counter_ns()
    if tool == "fast":
        value = truth("stale:" + text) if unreliable else truth(text)
    elif tool == "backup":
        # A separate direct path shares the hash primitive, not a stored answer.
        value = hashlib.sha256(bytes(text, encoding="utf-8")).hexdigest()
    else:
        raise ValueError("Unknown sandbox tool")
    return {"tool": tool, "value": value, "correct": value == truth(text),
            "elapsed_ns": time.perf_counter_ns() - started}


def grow(agent, channel):
    agent.step({"observations": [{"id": f"grow_{channel}", "channel": channel,
                                 "cost": 3.0, "source": "MORPH-003-bootstrap-fixture"}]})


def history_worker(path, regime, ordinal):
    if regime not in ("reliable", "unreliable") or ordinal not in (1, 2, 3):
        raise ValueError("Invalid calibration session")
    started = time.time_ns()
    agent = load(path)
    result = execute_tool("fast", f"calibration-{ordinal}", regime == "unreliable")
    outcome = agent.step({"now": float(ordinal), "session_boundary": True,
                          "domain_outcome": {"domain": "fast_checksum", "success": result["correct"]}})
    save(agent, path)
    return {"session": ordinal, "worker_pid": os.getpid(), "started_ns": started,
            "ended_ns": time.time_ns(), "execution": result,
            "feedback_derived_from_execution": True, "engineer": outcome["engineer"]}


def menu(domain="fast_checksum"):
    return [{"id": "fast", "value": 1.5, "risk": 0.1, "cost": 0.6, "affordance": domain},
            {"id": "backup", "value": 1.2, "risk": 0.1, "cost": 0.6}]


def evaluate(agent, regime, mode, text, context):
    clone = deepcopy(agent)
    memory = clone.mounted_organs["episodic_path_graph"]
    native = deepcopy(memory.state["domains"])
    if mode in ("memory_lesion", "memory_restored"):
        memory.state["domains"] = {}
    if mode == "memory_restored":
        memory.state["domains"] = native
    if mode == "coupling_disabled":
        arbiter = clone.mounted_organs["homeostatic_stakes_arbiter"]
        original = arbiter.process
        def bypass(data, turn, now, budget):
            return original({k: v for k, v in data.items() if k != "_learned_policy"}, turn, now, budget)
        arbiter.process = bypass
    clone.audit.append("experiment_intervention", clone.msv.current_turn,
                       {"mode": mode, "context": context})
    started = time.perf_counter_ns()
    result = clone.step({"domain": "fast_checksum", "tasks": menu()})
    selected = result["engineer"]["outputs"]["selected"]
    if len(selected) != 1:
        raise AssertionError("Expected one budget-permitted task")
    executed = execute_tool(selected[0], text, regime == "unreliable")
    return {"mode": mode, "context": context, "current_menu_sha256": hashlib.sha256(canonical(menu())).hexdigest(),
            "selected": selected[0], "execution": executed,
            "policy_elapsed_ns": time.perf_counter_ns() - started,
            "subject_text": result["subject_text"], "engineer": result["engineer"]}


def run_consequence_assay():
    regimes = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        seed = MorphZygote("MORPH-003-founder")
        grow(seed, "retrieval_loss")
        grow(seed, "resource_collision")
        boot = hashlib.sha256(canonical(state(seed))).hexdigest()
        for regime in ("reliable", "unreliable"):
            path = root / (regime + ".json")
            save(seed, path)
            histories = []
            for ordinal in (1, 2, 3):
                child = subprocess.run([sys.executable, "-m", __name__, "history", str(path), regime, str(ordinal)],
                                       text=True, capture_output=True, check=True)
                histories.append(json.loads(child.stdout))
            agent = load(path)
            trials = []
            for context, text in (("delayed_inventory", "inventory-item-47"),
                                  ("delayed_catalogue", "catalogue-object-93"),
                                  ("transfer_garden", "garden-sample-128")):
                agent.step({"scratchpad": {"unrelated": "intervening work"}})
                save(agent, path)
                agent = load(path)
                before = canonical(state(agent))
                for mode in MODES:
                    trials.append(evaluate(agent, regime, mode, text, context))
                if canonical(state(agent)) != before:
                    raise AssertionError("Study evaluation changed source state")
            regimes.append({"regime": regime, "common_boot_sha256": boot, "history": histories,
                            "evaluation_source_unchanged": True, "trials": trials})
    return {"schema_version": 1, "experiment": "MORPH-003", "protocol_sha256": PROTOCOL_SHA256,
            "article_source_sha256": load_contract()["source"]["sha256"],
            "classification": "author-designed restart-separated engineering mechanism assay",
            "real_days_elapsed": False, "host_clock_is_simulated": True, "independent_holdout": False,
            "foundation_models": "none; deterministic first-person formatter", "regimes": regimes,
            "full_article_assessment": assess_all({}, artifact_root=Path.cwd()),
            "claim_limit": "Actual pure-tool correctness and choice effects, not an independent ecological or all-Article qualification."}


def main():
    if len(sys.argv) != 5 or sys.argv[1] != "history":
        raise SystemExit("This worker accepts history SNAPSHOT REGIME ORDINAL")
    print(json.dumps(history_worker(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]))))


if __name__ == "__main__":
    main()
