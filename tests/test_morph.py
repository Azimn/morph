import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from morph_engine.core.zygote import MorphZygote
from morph_engine.core.persistence import load, save, state
from morph_engine.core.msv import AuditLog, canonical
from morph_engine.benchmark import run_benchmark


def grow(agent, channel):
    return agent.step({"observations": [{"id": f"obs_{len(agent.audit.events)}", "channel": channel,
                                        "cost": 3.0, "source": "test_fixture"}]})


def output(agent, data):
    return agent.step(data)["engineer"]["outputs"]


class DevelopmentTests(unittest.TestCase):
    def test_fresh_interpreter_import_boundary(self):
        subprocess.run([sys.executable, "-c", '''import sys, threading
from morph_engine.core.zygote import MorphZygote
z = MorphZygote("boot")
assert z.mounted_organs == {}
assert threading.active_count() == 1
assert not any(n.startswith("morph_engine.genome.") for n in sys.modules)
assert all(z.probe(n)["outcome"] == "UNASSESSABLE" for n in range(1,35))
'''], check=True)

    def test_all_article_stopping_rules(self):
        a = MorphZygote("a")
        r = a.step({"probes": list(range(1, 35))})
        self.assertEqual(len(r["engineer"]["probes"]), 34)
        self.assertTrue(all(p["reason"] == "organ_absent" for p in r["engineer"]["probes"]))
        grow(a, "retrieval_loss")
        self.assertEqual(a.probe(4)["reason"], "article_protocol_not_supplied")
        self.assertEqual(a.probe(4)["outcome"], "UNASSESSABLE")

    def test_threshold_and_growth_boundary(self):
        a = MorphZygote("a")
        a.step({"observations": [{"id": "a", "channel": "retrieval_loss", "cost": 1.2, "source": "test"}]})
        self.assertEqual(a.mounted_organs, {})
        r = grow(a, "retrieval_loss")
        self.assertEqual(r["engineer"]["mounted_before"], [])
        self.assertIn("episodic_path_graph", r["engineer"]["mounted_after"])

    def test_no_audit_replay_migration(self):
        a = MorphZygote("a")
        a.step({"scratchpad": {"secret": "past"}, "remember": {"key": "x", "value": "past"}})
        grow(a, "retrieval_loss")
        self.assertIsNone(output(a, {"recall": "x"})["recalled"])
        self.assertEqual(a.msv.scratchpad, {})

    def test_recall_after_development(self):
        a = MorphZygote("a")
        grow(a, "retrieval_loss")
        a.step({"remember": {"key": "x", "value": "fact"}})
        self.assertEqual(output(a, {"session_boundary": True, "recall": "x"})["recalled"]["value"], "fact")

    def test_path_dependence_and_style_substitution(self):
        a = MorphZygote("a")
        grow(a, "retrieval_loss")
        for domain, outcomes in (("fall", [True, True, False, False]), ("rise", [False, False, True, True])):
            for success in outcomes:
                a.step({"domain_outcome": {"domain": domain, "success": success}})
        fall = output(a, {"domain": "fall"})["memory_policy"]
        rise = output(a, {"domain": "rise"})["memory_policy"]
        self.assertGreater(fall["reserve"], rise["reserve"])
        self.assertEqual((fall["verification"], rise["verification"]), ("STRICT", "STANDARD"))
        a.renderer.style = "plain"
        self.assertEqual(output(a, {"domain": "fall"})["memory_policy"], fall)

    def test_macro_executes_after_five_verified_repetitions(self):
        a = MorphZygote("a")
        grow(a, "deliberation_tax")
        w = {"id": "w", "steps": [["add", 3], ["multiply", 2]], "input": 2, "expected": 10}
        for _ in range(4):
            a.step({"workflow": w})
        self.assertFalse(output(a, {"run_macro": {"id": "w", "input": 2}})["macro"])
        a.step({"workflow": w})
        self.assertEqual(output(a, {"run_macro": {"id": "w", "input": 4}})["result"], 14)
        self.assertFalse(output(a, {"run_macro": {"id": "w", "input": 2, "perturbed": True}})["macro"])

    def test_incorrect_workflow_not_learned(self):
        a = MorphZygote("a")
        grow(a, "deliberation_tax")
        for _ in range(6):
            a.step({"workflow": {"id": "w", "steps": [["add", 3]], "input": 2, "expected": 99}})
        self.assertFalse(output(a, {"run_macro": {"id": "w", "input": 2}})["macro"])

    def test_scheduler_budget_and_idempotency(self):
        a = MorphZygote("a")
        self.assertEqual(a.tick(0, 1)["status"], "UNASSESSABLE")
        grow(a, "boundary_drop")
        for i in range(3):
            a.step({"new_goal": {"id": str(i), "due": 10}})
        reserve = a.msv.reserve
        self.assertEqual(a.tick(10, 0)["due"], [])
        self.assertEqual(len(a.tick(10, 0.1)["due"]), 1)
        self.assertAlmostEqual(a.msv.reserve, reserve - 0.1)
        self.assertEqual(len(a.tick(10, 1)["due"]), 2)
        self.assertEqual(a.tick(10, 1)["due"], [])
        with self.assertRaises(ValueError):
            a.tick(9, 1)

    def test_completed_goal_never_emits(self):
        a = MorphZygote("a")
        grow(a, "boundary_drop")
        a.step({"new_goal": {"id": "x", "due": 10}})
        a.step({"complete_goal": "x"})
        self.assertEqual(a.tick(10, 1)["due"], [])

    def test_arbiter_budget_and_causal_clamp(self):
        a = MorphZygote("a")
        grow(a, "resource_collision")
        tasks = [{"id": "risky", "value": 2.0, "risk": 1.0, "cost": 0.7},
                 {"id": "safe", "value": 1.2, "risk": 0.0, "cost": 0.7}]
        a.intervene("homeostatic_stakes_arbiter", "caution", 0.0)
        low = output(a, {"tasks": tasks})
        a.intervene("homeostatic_stakes_arbiter", "caution", 1.0)
        high = output(a, {"tasks": tasks})
        self.assertEqual(low["selected"], ["risky"])
        self.assertEqual(high["selected"], ["safe"])
        self.assertLessEqual(high["task_cost"], a.msv.budget_per_turn)

    def test_partner_isolation_and_repair(self):
        a = MorphZygote("a")
        grow(a, "social_variance")
        first = output(a, {"partner": "A", "dropped_commitment": True, "witnessed": ["private"],
                           "norms": {"hello": "local"}, "shared_mishap": "spill"})
        repair = output(a, {"partner": "A", "apology": True})
        self.assertLess(repair["partner_reliability"], 0.75)
        self.assertGreater(repair["partner_reliability"], first["partner_reliability"])
        other = output(a, {"partner": "B", "callback_cue": "spill"})
        self.assertEqual(other["known_facts"], [])
        self.assertEqual(other["norms"], {})
        self.assertIsNone(other["callback"])

    def test_audit_is_prospective_and_calibrated(self):
        a = MorphZygote("a")
        grow(a, "epistemic_fog")
        self.assertFalse(output(a, {"audit_decision": "old"})["trace_found"])
        grow(a, "resource_collision")
        r = a.step({"tasks": [{"id": "x", "value": 2, "risk": 0, "cost": 0.2}]})
        trace = output(a, {"audit_decision": f"decision_{r['engineer']['turn']}"})
        self.assertEqual(trace["decision_trace"]["selected"], ["x"])
        self.assertAlmostEqual(output(a, {"confidence_outcome": {"confidence": 0.9, "success": False}})["brier_score"], 0.81)

    def test_prune_rebirth_no_resurrection(self):
        a = MorphZygote("a")
        grow(a, "retrieval_loss")
        a.step({"remember": {"key": "x", "value": "lost"}})
        for _ in range(17):
            a.step({})
        self.assertNotIn("episodic_path_graph", a.mounted_organs)
        grow(a, "retrieval_loss")
        self.assertIsNone(output(a, {"recall": "x"})["recalled"])
        genesis = [e for e in a.audit.events if e["kind"] == "genesis"]
        self.assertEqual(len(genesis), 2)
        self.assertNotEqual(genesis[0]["hash"], genesis[1]["hash"])

    def test_empty_calls_do_not_keep_arbiter_alive(self):
        a = MorphZygote("a")
        grow(a, "resource_collision")
        for _ in range(17):
            a.step({})
        self.assertEqual(a.mounted_organs, {})

    def test_no_growth_when_unaffordable(self):
        a = MorphZygote("a")
        a.msv.reserve = a.msv.budget_per_turn = 0
        grow(a, "boundary_drop")
        self.assertEqual(a.mounted_organs, {})
        self.assertGreater(a.msv.gradients["boundary_drop"], 0)

    def test_insolvency_prunes(self):
        a = MorphZygote("a")
        grow(a, "resource_collision")
        a.msv.reserve = a.msv.budget_per_turn = 0
        a.step({})
        self.assertEqual(a.mounted_organs, {})

    def test_duplicate_receipt_rejected_before_mutation(self):
        a = MorphZygote("a")
        e = {"id": "x", "channel": "boundary_drop", "cost": 1, "source": "fixture"}
        a.step({"observations": [e]})
        before = canonical(state(a))
        with self.assertRaises(ValueError):
            a.step({"observations": [e]})
        self.assertEqual(before, canonical(state(a)))

    def test_bad_inputs_atomic(self):
        for data in ({"now": -1}, {"now": float("nan")}, {"probes": [35]},
                     {"tasks": [{"id": "x", "value": 1, "risk": 0, "cost": -1}]},
                     {"observations": [{"id": "x", "channel": "boundary_drop", "cost": -1, "source": "f"}]},
                     {"run_macro": {"id": "x", "input": "bad"}}, {"partner": {}},
                     {"workflow": {"id": "w", "steps": [["shell", 1]], "input": 0, "expected": 0}}):
            a = MorphZygote("a")
            before = canonical(state(a))
            with self.assertRaises(ValueError):
                a.step(data)
            self.assertEqual(before, canonical(state(a)))

    def test_subject_boundary_and_output_aliases(self):
        a = MorphZygote("a")
        grow(a, "social_variance")
        r = a.step({"partner": "I remember my past life", "witnessed": ["I am conscious"]})
        for text in ("I remember", "I am conscious", "social_cultural", "caution", "reserve"):
            self.assertNotIn(text, r["subject_text"])
        r["engineer"]["outputs"]["known_facts"].append("injected")
        self.assertNotIn("injected", output(a, {"partner": "I remember my past life"})["known_facts"])

    def test_audit_copy_and_tamper(self):
        a = MorphZygote("a")
        grow(a, "retrieval_loss")
        events = a.audit.events
        events[0]["payload"]["cost"] = 99
        a.audit.verify()
        with self.assertRaises(ValueError):
            AuditLog(events)

    def test_snapshot_roundtrip_continues_identically(self):
        a = MorphZygote("a")
        for channel in ("retrieval_loss", "boundary_drop", "social_variance"):
            grow(a, channel)
        a.step({"remember": {"key": "x", "value": [1, 2]}, "partner": "A", "witnessed": ["fact"],
                "new_goal": {"id": "due", "due": 10}})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            save(a, path)
            b = load(path)
            self.assertEqual(state(a), state(b))
            data = {"recall": "x", "partner": "A", "session_boundary": True}
            self.assertEqual(a.step(data), b.step(data))
            self.assertEqual(a.tick(10, 1), b.tick(10, 1))

    def test_snapshot_corruption_and_version(self):
        a = MorphZygote("a")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "s.json"
            save(a, path)
            e = json.loads(path.read_text())
            e["state"]["msv"]["reserve"] = 9
            path.write_text(json.dumps(e))
            with self.assertRaises(ValueError):
                load(path)
            e["state"]["version"] = 99
            e["sha256"] = hashlib.sha256(canonical(e["state"])).hexdigest()
            path.write_text(json.dumps(e))
            with self.assertRaises(ValueError):
                load(path)

    def test_empty_snapshot_restore_keeps_modules_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.json"
            save(MorphZygote("a"), path)
            script = ("import sys; from morph_engine.core.persistence import load; "
                      f"a = load({str(path)!r}); "
                      "assert not a.mounted_organs; "
                      "assert not any(n.startswith('morph_engine.genome.') for n in sys.modules)")
            subprocess.run([sys.executable, "-c", script], check=True)

    def test_all_six_organs_survive_checkpoint(self):
        a = MorphZygote("a")
        for spec in a.ame.catalog:
            grow(a, spec["channel"])
        a.step({"partner": "A", "witnessed": ["fact"], "conflict": "unresolved",
                "domain_outcome": {"domain": "supplier", "success": True}})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "six.json"
            save(a, path)
            b = load(path)
            self.assertEqual(state(a), state(b))
            self.assertEqual(len(b.mounted_organs), 6)
            data = {"partner": "A", "domain": "supplier", "audit_decision": "absent"}
            self.assertEqual(a.step(data), b.step(data))

    def test_growth_disabled_control_keeps_empty_topology(self):
        a = MorphZygote("a", growth_enabled=False)
        for spec in a.ame.catalog:
            grow(a, spec["channel"])
        self.assertEqual(a.mounted_organs, {})
        self.assertFalse(any(e["kind"] == "genesis" for e in a.audit.events))

    def test_failed_atomic_replace_preserves_previous_snapshot(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            a = MorphZygote("a")
            save(a, path)
            old = path.read_bytes()
            a.step({})
            with patch("morph_engine.core.persistence.os.replace", side_effect=OSError("fixture")):
                with self.assertRaises(OSError):
                    save(a, path)
            self.assertEqual(path.read_bytes(), old)
            self.assertEqual(len(list(Path(temp).iterdir())), 1)
            self.assertEqual(load(path).msv.current_turn, 0)

    def test_macro_overflow_rejected_before_turn_mutation(self):
        a = MorphZygote("a")
        grow(a, "deliberation_tax")
        for _ in range(5):
            a.step({"workflow": {"id": "large", "steps": [["multiply", 1e200]],
                                 "input": 1.0, "expected": 1e200}})
        before = canonical(state(a))
        with self.assertRaises(ValueError):
            a.step({"run_macro": {"id": "large", "input": 1e200}})
        self.assertEqual(before, canonical(state(a)))

    def test_longitudinal_reproducibility(self):
        r = run_benchmark()
        self.assertEqual(r, run_benchmark())
        self.assertTrue(r["same_boot"])
        self.assertTrue(r["pairwise_different"])
        self.assertEqual([len(x["history"]) for x in r["lineages"]], [30, 30, 30])
        for lineage, control in zip(r["lineages"], r["growth_disabled_controls"]):
            self.assertEqual(control["organs"], [])
            for channel, failures in lineage["failures"].items():
                self.assertLess(failures, control["failures"][channel])
            self.assertTrue(all(p["outcome"] == "UNASSESSABLE" for p in lineage["articles"]))
        a, b, c = [set(x["organs"]) for x in r["lineages"]]
        self.assertIn("chronos_daemon", a)
        self.assertNotIn("chronos_daemon", b)
        self.assertIn("social_cultural_cortex", c)
        self.assertNotIn("social_cultural_cortex", a)


if __name__ == "__main__":
    unittest.main()
