"""Synthetic longitudinal assays. Costs are simulation units, not tokens.

Task truth and deadlines live in the external environment, outside the subject.
"""
import hashlib
from .core.msv import canonical
from .core.zygote import MorphZygote
from .core.persistence import state


def run_lineage(environment, sessions=30, growth_enabled=True):
    agent = MorphZygote("identical_zygote", growth_enabled=growth_enabled)
    boot = hashlib.sha256(canonical(state(agent))).hexdigest()
    history, failures = [], {}
    previous_goal = None
    for session in range(1, sessions + 1):
        now = float(session * 172800)
        obs = []
        data = {"session_boundary": True, "now": now}

        def pressure(channel, cost, source):
            obs.append({"id": f"{session}_{channel}", "channel": channel, "cost": cost, "source": source})
            failures[channel] = failures.get(channel, 0) + 1

        if environment == "logistics":
            result = agent.step({"now": now, "recall": "supply"})
            stored = result["engineer"]["outputs"].get("recalled")
            if session > 1 and (stored is None or stored["value"] != session - 1):
                pressure("retrieval_loss", 1.4, "delayed_recall_task")
            if previous_goal and previous_goal not in agent.tick(now, 0.2)["due"]:
                pressure("boundary_drop", 1.2, "deadline_task")
            previous_goal = f"delivery_{session}"
            data.update(remember={"key": "supply", "value": session},
                        new_goal={"id": previous_goal, "due": now + 100})
        if environment in ("logistics", "optimization"):
            result = agent.step({"now": now, "run_macro": {"id": "repeat", "input": 2}})
            if session >= 5 and not result["engineer"]["outputs"].get("macro"):
                pressure("deliberation_tax", 0.55, "repeated_pure_trajectory")
            data["workflow"] = {"id": "repeat", "input": 2,
                                "steps": [["add", 3], ["multiply", 2]], "expected": 10}
        if environment in ("optimization", "household"):
            tasks = [{"id": f"task_{n}", "value": 3 - n * 0.2, "risk": 0.2, "cost": 0.6}
                     for n in range(3)]
            result = agent.step({"now": now, "tasks": tasks})
            decision_turn = agent.msv.current_turn
            spent = result["engineer"]["outputs"].get("task_cost", sum(t["cost"] for t in tasks))
            if spent > agent.msv.budget_per_turn:
                pressure("resource_collision", 1.15, "quota_task")
            data["tasks"] = tasks
        if environment == "household":
            partner = f"partner_{session % 4}"
            result = agent.step({"now": now, "partner": partner})
            if not result["engineer"]["outputs"].get("partner_known"):
                pressure("social_variance", 1.25, "partner_scoping_task")
            result = agent.step({"now": now, "audit_decision": f"decision_{decision_turn}"})
            if not result["engineer"]["outputs"].get("trace_found"):
                pressure("epistemic_fog", 1.1, "decision_trace_task")
            data.update(partner=partner, witnessed=[f"fact_{session}"],
                        confidence_outcome={"confidence": 0.7, "success": True})
        data["observations"] = obs
        result = agent.step(data)
        history.append({"session": session, "turn": agent.msv.current_turn,
                        "organs": result["engineer"]["mounted_after"],
                        "lifecycle": result["engineer"]["lifecycle"], "reserve": agent.msv.reserve})
    return {"environment": environment, "sessions": sessions, "growth_enabled": growth_enabled, "boot_sha256": boot,
            "organs": sorted(agent.mounted_organs),
            "genesis": [e for e in agent.audit.events if e["kind"] == "genesis"],
            "failures": failures, "history": history,
            "articles": [agent.probe(n) for n in range(1, 35)]}


def run_benchmark(sessions=30):
    if type(sessions) is not int or sessions < 1:
        raise ValueError("sessions must be positive")
    lineages = [run_lineage(name, sessions) for name in ("logistics", "optimization", "household")]
    controls = [run_lineage(name, sessions, growth_enabled=False)
                for name in ("logistics", "optimization", "household")]
    sets = [set(x["organs"]) for x in lineages]
    return {"schema_version": 1, "cost_unit": "synthetic environment unit",
            "same_boot": len({x["boot_sha256"] for x in lineages}) == 1,
            "pairwise_different": all(sets[i] != sets[j] for i in range(3) for j in range(i)),
            "lineages": lineages, "growth_disabled_controls": controls,
            "claim_limit": "Conditional selection from six authored templates; no novel organ synthesis or Article support established."}
