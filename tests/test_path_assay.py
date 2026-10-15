from copy import deepcopy
import hashlib
from pathlib import Path
import unittest
from morph_engine.path_assay import (PROTOCOL_SHA256, histories, matching, develop,
                                      evaluate, capture, run_path_assay)
from morph_engine.core.persistence import state


class MatchedOrderTests(unittest.TestCase):
    def test_frozen_protocol_matches_source(self):
        path = Path(__file__).resolve().parents[1] / "docs/protocols/MORPH-002-matched-event-order.md"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), PROTOCOL_SHA256)

    def test_atomic_event_swap_preserves_multiset_and_task_schedule(self):
        for case in ("pruning_only", "retained_memory"):
            arms = histories(case)
            gate = matching(arms)
            self.assertTrue(gate["same_event_multiset"])
            self.assertTrue(gate["execution_orders_differ"])
            self.assertAlmostEqual(gate["pressure_per_arm"], 2.8)
            for early, late in zip(arms["early"][2:10], arms["late"][2:10]):
                self.assertEqual(early, late)

    def test_matching_rejects_rewritten_payload(self):
        arms = histories("retained_memory")
        arms["late"][2]["payload"]["remember"]["value"] = "rewritten"
        self.assertFalse(matching(arms)["same_event_multiset"])

    def test_runtime_uses_delivered_order_not_event_identifier_order(self):
        arms = histories("pruning_only")
        early, _, et = develop(arms["early"], "developmental")
        late, _, lt = develop(arms["late"], "developmental")
        eb = [e["turn"] for e in early.audit.events if e["kind"] == "genesis"]
        lb = [e["turn"] for e in late.audit.events if e["kind"] == "genesis"]
        self.assertEqual(eb, [2])
        self.assertEqual(lb, [18])
        self.assertNotEqual([r["event_id"] for r in et], [r["event_id"] for r in lt])

    def test_nonmutating_evaluation_and_ablation(self):
        agent, _, _ = develop(histories("retained_memory")["early"], "developmental")
        before = deepcopy(state(agent))
        sham = evaluate(agent)
        lesion = evaluate(agent, True)
        self.assertEqual(state(agent), before)
        self.assertTrue(sham["source_state_unchanged"])
        self.assertTrue(lesion["source_state_unchanged"])
        self.assertEqual(lesion["correct"], 0)
        turns = [r["response"]["engineer"]["turn"] for r in sham["responses"]]
        self.assertEqual(len(set(turns)), 1)

    def test_late_growth_cannot_reconstruct_prebirth_content(self):
        agent, _, _ = develop(histories("retained_memory")["late"], "developmental")
        self.assertEqual(agent.mounted_organs["episodic_path_graph"].state["episodes"], {})
        self.assertEqual(evaluate(agent)["correct"], 0)

    def test_content_metric_excludes_receipt_and_birth_metadata(self):
        agent, _, _ = develop(histories("retained_memory")["early"], "fixed_memory")
        before = capture(agent, 0)["content_hashes"]
        agent.audit.append("test_only", agent.msv.current_turn, {"different": "receipt"})
        agent.mounted_organs["episodic_path_graph"].born = 1
        self.assertEqual(before, capture(agent, 0)["content_hashes"])

    def test_controls_and_repeated_execution_gates(self):
        report = run_path_assay()
        self.assertTrue(report["gates_passed"])
        for case in report["cases"]:
            for condition in case["conditions"]:
                self.assertTrue(condition["same_paired_boot"])
                self.assertTrue(condition["same_continuation_inputs"])
                for arm in (condition["early"], condition["late"]):
                    self.assertTrue(arm["identical_history_reproduced"])
                    self.assertEqual([c["continuation_age"] for c in arm["captures"]], [0, 8, 32, 64])
                    self.assertTrue(all(c["sham"]["source_state_unchanged"] for c in arm["captures"]))
                if condition["mode"] == "growth_disabled":
                    self.assertTrue(all(not c["topology"] for c in condition["early"]["captures"]))
                if condition["mode"] == "fixed_memory":
                    # Positive, null, or opposite developmental outcomes remain
                    # admissible; the control must isolate the moved pressures.
                    self.assertTrue(all(c["sham_recall_gap_early_minus_late"] == 0
                                        for c in condition["comparisons"]))

    def test_cli_preserves_complete_raw_report_and_derived_summary(self):
        import gzip
        import json
        import subprocess
        import sys
        import tempfile
        from morph_engine.path_assay import summarize
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "raw.json.gz"
            summary = Path(temp) / "summary.json"
            command = [sys.executable, "-m", "morph_engine", "path-assay", "--output", str(raw),
                       "--summary-output", str(summary)]
            subprocess.run(command, check=True, capture_output=True)
            first_bytes = raw.read_bytes()
            report = json.loads(gzip.decompress(first_bytes))
            self.assertEqual(summarize(report), json.loads(summary.read_text()))
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(first_bytes, raw.read_bytes())
