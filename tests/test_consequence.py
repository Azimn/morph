from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from morph_engine.consequence_assay import (PROTOCOL_SHA256, evaluate, execute_tool,
                                            grow, menu, run_consequence_assay)
from morph_engine.core.persistence import state
from morph_engine.core.msv import canonical
from morph_engine.core.zygote import MorphZygote


class ConsequentialMemoryTests(unittest.TestCase):
    def subject(self, arbiter_first=False):
        a = MorphZygote("test")
        for channel in (("resource_collision", "retrieval_loss") if arbiter_first
                        else ("retrieval_loss", "resource_collision")):
            grow(a, channel)
        for _ in range(3):
            a.step({"domain_outcome": {"domain": "fast_checksum", "success": False}})
        return a

    def test_frozen_protocol_digest(self):
        path=Path(__file__).resolve().parents[1]/"docs/protocols/MORPH-003-consequential-memory.md"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), PROTOCOL_SHA256)

    def test_memory_changes_executed_result_and_restore_recovers(self):
        a=self.subject()
        before=canonical(state(a))
        records={mode:evaluate(a,"unreliable",mode,"fresh task","transfer")
                 for mode in ("intact","memory_lesion","memory_restored","coupling_disabled")}
        self.assertEqual(records["intact"]["selected"],"backup")
        self.assertEqual(records["memory_lesion"]["selected"],"fast")
        self.assertEqual(records["memory_restored"]["selected"],"backup")
        self.assertEqual(records["coupling_disabled"]["selected"],"fast")
        self.assertTrue(records["intact"]["execution"]["correct"])
        self.assertFalse(records["memory_lesion"]["execution"]["correct"])
        self.assertEqual(before,canonical(state(a)))

    def test_explicit_dependency_order_independent_of_organ_birth_order(self):
        a=self.subject(arbiter_first=True)
        self.assertEqual(evaluate(a,"unreliable","intact","fresh","test")["selected"],"backup")

    def test_unmatched_domain_does_not_apply_learned_risk(self):
        a=self.subject()
        r=a.step({"domain":"fast_checksum","tasks":menu("unrelated_tool")})
        out=r["engineer"]["outputs"]
        self.assertEqual(out["selected"],["fast"])
        self.assertNotIn("applied_memory_risk",out)

    def test_private_signal_cannot_be_supplied_by_caller(self):
        a=self.subject();before=canonical(state(a))
        with self.assertRaises(ValueError):
            a.step({"_learned_policy":{"reliability":0.0}})
        self.assertEqual(before,canonical(state(a)))

    def test_ambiguous_affordance_identifier_rejected(self):
        a=self.subject();tasks=menu();tasks[0]["affordance"]={"tool":"x"}
        with self.assertRaises(ValueError):a.step({"tasks":tasks})

    def test_actual_tool_scoring_has_real_negative_condition(self):
        self.assertFalse(execute_tool("fast","source",True)["correct"])
        self.assertTrue(execute_tool("backup","source",True)["correct"])

    def test_restart_processes_and_all_article_stopping_rules(self):
        r=run_consequence_assay()
        self.assertFalse(r["full_article_assessment"]["all_claims_supported"])
        self.assertEqual(len(r["full_article_assessment"]["articles"]),34)
        for regime in r["regimes"]:
            self.assertEqual(len({s["worker_pid"] for s in regime["history"]}),3)
            self.assertTrue(regime["evaluation_source_unchanged"])
            self.assertEqual(len(regime["trials"]),15)
            for session in regime["history"]:
                self.assertTrue(session["feedback_derived_from_execution"])
                self.assertGreaterEqual(session["ended_ns"],session["started_ns"])
