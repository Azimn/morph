from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from morph_engine.qualification import assess_all, assess_article, hash_json, load_contract


class ArticleEvidenceContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.contract = load_contract()

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data))
        return dict(path=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def packet(self, *, opportunity=1, scope="longitudinal_deployment", good=True, **changes):
        spec = self.contract["articles"][21]
        comparisons = {name: dict(left=1, right=0, relation="gt") for name in spec["controls"]}
        comparisons["primary"] = dict(left=1 if good else 0, right=0, relation="gt")
        protocol = dict(article=22, scope=scope, source_sha256=self.contract["source"]["sha256"],
                        controls={k: k for k in spec["controls"]}, predictions=["primary"],
                        comparisons={k: dict(relation="gt") for k in comparisons})
        ref = self.write("protocol.json", protocol)
        observed = dict(article=22, protocol_sha256=ref["sha256"], opportunities=opportunity,
                        prerequisites={k: True for k in spec["prerequisites"]},
                        informative_alternatives=True, comparisons=comparisons,
                        history=dict(separated_history_sessions=3, delayed_opportunities=2,
                                     heldout_transfer_contexts=1))
        observed.update(changes)
        return dict(contract_sha256=hash_json(self.contract), protocol=ref,
                    observations=self.write("observations.json", observed))

    def test_canonical_34_and_embodiment_reflection_subcriteria(self):
        self.assertEqual([a["article"] for a in self.contract["articles"]], list(range(1,35)))
        self.assertIn("persistent_markers", self.contract["articles"][10]["prerequisites"])
        self.assertIn("convergent_profundity_control", self.contract["articles"][22]["controls"])

    def test_missing_evidence_produces_34_unassessable_not_passes(self):
        report = assess_all({}, artifact_root=self.root)
        self.assertEqual(len(report["articles"]), 34)
        self.assertFalse(report["all_claims_supported"])
        self.assertIsNone(report["consciousness_score"])
        self.assertTrue(all(r["outcome"]=="Unassessable" for r in report["articles"]))

    def test_registered_predictions_can_be_supported_in_scorer_fixture(self):
        self.assertEqual(assess_article(22,self.packet(),artifact_root=self.root)["outcome"],"Supported")

    def test_genuine_opportunity_with_adverse_result_is_unsupported(self):
        self.assertEqual(assess_article(22,self.packet(good=False),artifact_root=self.root)["outcome"],"Unsupported")

    def test_missing_opportunity_is_unassessable_not_unsupported(self):
        row=assess_article(22,self.packet(opportunity=0,good=False),artifact_root=self.root)
        self.assertEqual(row["outcome"],"Unassessable")

    def test_engineering_scope_cannot_become_full_article_support(self):
        self.assertEqual(assess_article(22,self.packet(scope="engineering"),artifact_root=self.root)["outcome"],"Unassessable")

    def test_no_informative_alternative_stops_assessment(self):
        self.assertEqual(assess_article(22,self.packet(informative_alternatives=False),artifact_root=self.root)["outcome"],"Unassessable")

    def test_insufficient_longitudinal_opportunities_stop_assessment(self):
        row=assess_article(22,self.packet(history={}),artifact_root=self.root)
        self.assertIn("delayed_opportunities",row["missing_prerequisites"])

    def test_artifact_tampering_and_wrong_contract_are_rejected(self):
        packet=self.packet()
        (self.root/"observations.json").write_text("{}")
        with self.assertRaises(ValueError):assess_article(22,packet,artifact_root=self.root)
        packet=self.packet();packet["contract_sha256"]="0"*64
        with self.assertRaises(ValueError):assess_article(22,packet,artifact_root=self.root)

    def test_artifact_path_escape_is_rejected(self):
        packet=self.packet();packet["observations"]["path"]="../outside.json"
        with self.assertRaises(ValueError):assess_article(22,packet,artifact_root=self.root)

    def test_wrong_article_and_unknown_article_are_rejected(self):
        packet=self.packet()
        with self.assertRaises(ValueError):assess_article(21,packet,artifact_root=self.root)
        with self.assertRaises(ValueError):assess_all({35:packet},artifact_root=self.root)
