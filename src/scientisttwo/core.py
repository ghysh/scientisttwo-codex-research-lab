from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = [
    "intake", "limitations", "seed_ideas", "baseline_subset", "subset_experiments",
    "full_set", "idea_evolution", "best_idea", "ablation", "draft", "peer_review",
    "rebuttal", "meta_review", "integrity_audit", "completed", "halted",
]

COUNTERS = {
    "limitations": "limitation_rounds",
    "subset_experiments": "subset_engineering_rounds",
    "idea_evolution": "idea_evolution_rounds",
    "ablation": "ablation_refinement_rounds",
    "peer_review": "peer_review_rounds",
    "rebuttal": "rebuttal_rounds",
    "integrity_audit": "audit_rounds",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "AGENTS.md").exists() and (candidate / ".codex").exists():
            return candidate
    raise FileNotFoundError("Could not find project root (AGENTS.md + .codex/). Run from the project folder.")


def state_path(root: Path) -> Path:
    return root / "research" / "state.json"


def load_state(root: Path) -> dict[str, Any]:
    p = state_path(root)
    if not p.exists():
        raise FileNotFoundError("research/state.json is missing. Run `st2 init` first.")
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    p = state_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def append_event(root: Path, event: dict[str, Any]) -> None:
    ledger = root / "research" / "ledger" / "events.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": now(), **event}
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_budget(root: Path) -> dict[str, Any]:
    import tomllib
    p = root / "research" / "budget.toml"
    if not p.exists():
        return {"limits": {}}
    with p.open("rb") as f:
        return tomllib.load(f)


def init_state(root: Path, problem_file: str) -> dict[str, Any]:
    p = root / problem_file
    if not p.exists():
        raise FileNotFoundError(f"Problem file not found: {problem_file}")
    target = state_path(root)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("status") != "uninitialized":
            raise FileExistsError("State is already initialized. Archive state.json and ledger before reinitializing.")
    state = {
        "schema_version": 1,
        "project": root.name,
        "status": "active",
        "current_stage": "intake",
        "created_at": now(),
        "updated_at": now(),
        "problem_file": problem_file,
        "counters": {
            "limitation_rounds": 0,
            "subset_engineering_rounds": 0,
            "idea_evolution_rounds": 0,
            "successful_ideas": 0,
            "ablation_refinement_rounds": 0,
            "peer_review_rounds": 0,
            "review_driven_refinement_rounds": 0,
            "rebuttal_rounds": 0,
            "audit_rounds": 0,
        },
        "candidates": [],
        "experiments": [],
        "best_candidate_id": None,
        "pending_ablation_refinement": False,
        "gate_history": [],
    }
    save_state(root, state)
    append_event(root, {"type": "project_initialized", "problem_file": problem_file})
    return state


def _limit_reached(state: dict[str, Any], counter: str, limit: int) -> bool:
    return int(state.get("counters", {}).get(counter, 0)) >= int(limit)


def apply_gate(root: Path, stage: str, decision: str, feedback: str, score: float | None = None, candidate_id: str | None = None, comparison: str | None = None) -> dict[str, Any]:
    state = load_state(root)
    current = state["current_stage"]
    if stage != current:
        raise ValueError(f"Gate stage mismatch: state is at '{current}', not '{stage}'.")
    decision = decision.lower().strip()
    budget = read_budget(root).get("limits", {})
    counters = state["counters"]
    next_stage = current
    status = "active"

    rules: dict[str, set[str]] = {
        "intake": {"accept", "refine", "reject"},
        "limitations": {"accept", "refine", "reject"},
        "seed_ideas": {"accept", "refine", "reject"},
        "baseline_subset": {"accept", "refine", "reject"},
        "subset_experiments": {"bad", "good", "engineer"},
        "full_set": {"accept", "refine", "reject"},
        "idea_evolution": {"accept", "refine", "reject"},
        "best_idea": {"accept", "refine", "reject"},
        "ablation": {"good", "refine", "reject"},
        "draft": {"accept", "refine", "reject"},
        "peer_review": {"accept", "refine", "reject"},
        "rebuttal": {"accept", "refine", "reject"},
        "meta_review": {"accept", "refine", "reject"},
        "integrity_audit": {"accept", "refine", "reject"},
    }
    if current not in rules:
        raise ValueError(f"No gate is available at stage '{current}'.")
    if decision not in rules[current]:
        raise ValueError(f"Decision '{decision}' invalid for '{current}'. Allowed: {sorted(rules[current])}")
    if current == "peer_review" and score is None:
        raise ValueError("Peer-review gates require --score so the configured acceptance threshold can be applied.")
    candidate = None
    if candidate_id:
        candidate = next((c for c in state.get("candidates", []) if c.get("id") == candidate_id), None)
        if candidate is None:
            raise ValueError(f"Unknown candidate id: {candidate_id}")
    if current in {"subset_experiments", "full_set", "best_idea"} and candidate is None:
        raise ValueError(f"Gate '{current}' requires --candidate <candidate_id>.")

    if current == "intake":
        next_stage = {"accept": "limitations", "refine": "intake", "reject": "halted"}[decision]
    elif current == "limitations":
        counters["limitation_rounds"] += 1
        if decision == "accept": next_stage = "seed_ideas"
        elif decision == "refine" and _limit_reached(state, "limitation_rounds", budget.get("limitation_extraction_max_rounds", 16)): next_stage = "halted"; status = "halted"
        elif decision == "refine": next_stage = "limitations"
        else: next_stage = "halted"; status = "halted"
    elif current == "seed_ideas":
        next_stage = {"accept": "baseline_subset", "refine": "seed_ideas", "reject": "halted"}[decision]
        if decision == "reject": status = "halted"
    elif current == "baseline_subset":
        next_stage = {"accept": "subset_experiments", "refine": "baseline_subset", "reject": "halted"}[decision]
        if decision == "reject": status = "halted"
    elif current == "subset_experiments":
        if decision == "good":
            candidate["status"] = "subset_good"
            next_stage = "full_set"
        elif decision == "bad":
            candidate["status"] = "bad"
            next_stage = "idea_evolution"
        else:
            candidate["engineering_rounds"] = int(candidate.get("engineering_rounds", 0)) + 1
            counters["subset_engineering_rounds"] += 1
            if candidate["engineering_rounds"] >= int(budget.get("subset_engineering_max_rounds", 2)):
                candidate["status"] = "bad"
                next_stage = "idea_evolution"
            else: next_stage = "subset_experiments"
    elif current == "full_set":
        if state.get("pending_ablation_refinement"):
            if decision == "accept" and comparison not in {"update_best", "keep_old"}:
                raise ValueError("After ablation refinement, full-set acceptance requires --comparison update_best or keep_old from result_comparator.")
            if decision == "accept" and comparison == "update_best":
                previous_best_id = state.get("best_candidate_id")
                if previous_best_id and previous_best_id != candidate_id:
                    previous_best = next((c for c in state.get("candidates", []) if c.get("id") == previous_best_id), None)
                    if previous_best is not None:
                        previous_best["status"] = "superseded"
                candidate["status"] = "best_selected"
                state["best_candidate_id"] = candidate_id
            elif decision in {"accept", "reject"}:
                candidate["status"] = "rejected_refinement"
            if decision in {"accept", "reject"}:
                state["pending_ablation_refinement"] = False
                next_stage = "ablation"
            else:
                next_stage = "full_set"
        else:
            if decision == "accept":
                if candidate.get("status") not in {"full_validated", "best_selected"}:
                    counters["successful_ideas"] += 1
                candidate["status"] = "full_validated"
            elif decision == "reject": candidate["status"] = "bad"
            next_stage = {"accept": "idea_evolution", "refine": "full_set", "reject": "idea_evolution"}[decision]
    elif current == "idea_evolution":
        counters["idea_evolution_rounds"] += 1
        successes = int(counters.get("successful_ideas", 0))
        max_rounds = int(budget.get("idea_evolution_max_rounds", 4))
        if decision == "reject":
            next_stage = "best_idea" if successes > 0 else "halted"
            if successes == 0: status = "halted"
        elif successes >= int(budget.get("early_stop_successful_ideas", 4)):
            next_stage = "best_idea"
        elif counters["idea_evolution_rounds"] >= max_rounds:
            next_stage = "best_idea" if successes > 0 else "halted"
            if successes == 0: status = "halted"
        elif decision == "refine":
            next_stage = "idea_evolution"
        else:
            next_stage = "subset_experiments"
    elif current == "best_idea":
        if decision == "accept":
            if candidate.get("status") != "full_validated":
                raise ValueError("Only a full_validated candidate can be selected as best.")
            state["best_candidate_id"] = candidate_id
            candidate["status"] = "best_selected"
        next_stage = {"accept": "ablation", "refine": "idea_evolution", "reject": "halted"}[decision]
        if decision == "reject": status = "halted"
    elif current == "ablation":
        if decision == "good": next_stage = "draft"
        elif decision == "reject": next_stage = "halted"; status = "halted"
        else:
            max_ablation_refinements = int(budget.get("ablation_refinement_max_rounds", 1))
            if counters["ablation_refinement_rounds"] >= max_ablation_refinements:
                next_stage = "halted"
                status = "halted"
            else:
                counters["ablation_refinement_rounds"] += 1
                state["pending_ablation_refinement"] = True
                next_stage = "full_set"
    elif current == "draft":
        next_stage = {"accept": "peer_review", "refine": "draft", "reject": "halted"}[decision]
        if decision == "reject": status = "halted"
    elif current == "peer_review":
        counters["peer_review_rounds"] += 1
        threshold = float(budget.get("peer_review_acceptance_score", 8.0))
        if decision == "accept" and score is not None and score >= threshold: next_stage = "meta_review"
        elif counters["peer_review_rounds"] < int(budget.get("peer_review_max_rounds", 2)): next_stage = "rebuttal"
        else: next_stage = "meta_review"
    elif current == "rebuttal":
        counters["rebuttal_rounds"] += 1
        if decision == "accept": next_stage = "peer_review"
        elif decision == "refine": next_stage = "rebuttal"
        else: next_stage = "peer_review"
    elif current == "meta_review":
        next_stage = {"accept": "integrity_audit", "refine": "idea_evolution", "reject": "halted"}[decision]
        if decision == "reject": status = "halted"
        elif decision == "refine":
            counters["review_driven_refinement_rounds"] += 1
            if counters["review_driven_refinement_rounds"] > int(budget.get("review_driven_idea_refinement_max_rounds", 1)):
                next_stage = "halted"
                status = "halted"
    elif current == "integrity_audit":
        counters["audit_rounds"] += 1
        if decision == "accept":
            report_path = root / "research" / "audit" / "audit-report.json"
            if not report_path.exists():
                raise ValueError("Cannot accept integrity audit: research/audit/audit-report.json is missing.")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("overall") != "PASS":
                raise ValueError("Cannot accept integrity audit: latest audit report is not PASS.")
        next_stage = {"accept": "completed", "refine": "integrity_audit", "reject": "halted"}[decision]
        if decision == "reject": status = "halted"
        if decision == "accept": status = "completed"

    gate = {"stage": current, "decision": decision, "feedback": feedback, "score": score, "candidate_id": candidate_id, "next_stage": next_stage, "timestamp": now()}
    state["gate_history"].append(gate)
    state["current_stage"] = next_stage
    state["status"] = status
    save_state(root, state)
    append_event(root, {"type": "gate", **gate})
    return state


def add_candidate(root: Path, candidate_id: str, limitation: str, hypothesis: str, novelty: float | None) -> dict[str, Any]:
    state = load_state(root)
    if any(c["id"] == candidate_id for c in state["candidates"]):
        raise ValueError(f"Candidate already exists: {candidate_id}")
    candidate = {"id": candidate_id, "limitation": limitation, "hypothesis": hypothesis, "novelty_score": novelty, "status": "proposed", "engineering_rounds": 0, "created_at": now()}
    state["candidates"].append(candidate)
    save_state(root, state)
    append_event(root, {"type": "candidate_added", **candidate})
    return candidate
