import json
import tempfile
import unittest
from pathlib import Path

from scientisttwo.core import init_state, apply_gate, load_state


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".codex").mkdir()
        (self.root / "research").mkdir()
        (self.root / "research" / "problem.md").write_text("problem", encoding="utf-8")
        (self.root / "research" / "budget.toml").write_text("[limits]\nlimitation_extraction_max_rounds=2\nidea_evolution_max_rounds=2\nsubset_engineering_max_rounds=1\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("rules", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_and_intake_gate(self):
        init_state(self.root, "research/problem.md")
        state = apply_gate(self.root, "intake", "accept", "complete")
        self.assertEqual(state["current_stage"], "limitations")
        self.assertEqual(load_state(self.root)["status"], "active")

    def test_stage_mismatch_rejected(self):
        init_state(self.root, "research/problem.md")
        with self.assertRaises(ValueError):
            apply_gate(self.root, "limitations", "accept", "wrong stage")

    def test_bad_subset_moves_to_evolution(self):
        init_state(self.root, "research/problem.md")
        state = load_state(self.root)
        state["current_stage"] = "subset_experiments"
        state["candidates"].append({"id": "H001", "status": "proposed", "engineering_rounds": 0})
        (self.root / "research" / "state.json").write_text(json.dumps(state), encoding="utf-8")
        state = apply_gate(self.root, "subset_experiments", "bad", "candidate underperforms", candidate_id="H001")
        self.assertEqual(state["current_stage"], "idea_evolution")

    def test_idea_evolution_stops_when_no_successful_ideas(self):
        init_state(self.root, "research/problem.md")
        state = load_state(self.root)
        state["current_stage"] = "idea_evolution"
        (self.root / "research" / "state.json").write_text(json.dumps(state), encoding="utf-8")
        state = apply_gate(self.root, "idea_evolution", "accept", "round one complete")
        self.assertEqual(state["current_stage"], "subset_experiments")
        state["current_stage"] = "idea_evolution"
        (self.root / "research" / "state.json").write_text(json.dumps(state), encoding="utf-8")
        state = apply_gate(self.root, "idea_evolution", "accept", "round two complete")
        self.assertEqual(state["current_stage"], "halted")
        self.assertEqual(state["status"], "halted")

    def test_peer_review_requires_numeric_score(self):
        init_state(self.root, "research/problem.md")
        state = load_state(self.root)
        state["current_stage"] = "peer_review"
        (self.root / "research" / "state.json").write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(ValueError):
            apply_gate(self.root, "peer_review", "accept", "missing score")

    def test_ablation_refinement_returns_to_ablation_after_comparison(self):
        init_state(self.root, "research/problem.md")
        state = load_state(self.root)
        state["current_stage"] = "ablation"
        state["best_candidate_id"] = "H001"
        state["candidates"].append({"id": "H001", "status": "best_selected", "engineering_rounds": 0})
        state["candidates"].append({"id": "H002", "status": "proposed", "engineering_rounds": 0})
        (self.root / "research" / "state.json").write_text(json.dumps(state), encoding="utf-8")
        state = apply_gate(self.root, "ablation", "refine", "ablation suggests refinement")
        self.assertEqual(state["current_stage"], "full_set")
        self.assertTrue(state["pending_ablation_refinement"])
        state = apply_gate(self.root, "full_set", "accept", "new full-set run is better", candidate_id="H002", comparison="update_best")
        self.assertEqual(state["current_stage"], "ablation")
        self.assertFalse(state["pending_ablation_refinement"])
        self.assertEqual(state["best_candidate_id"], "H002")
        self.assertEqual(next(c for c in state["candidates"] if c["id"] == "H001")["status"], "superseded")


if __name__ == "__main__":
    unittest.main()
