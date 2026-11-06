from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from .audit import run_audit
from .core import STAGES, add_candidate, apply_gate, init_state, load_state, repo_root
from .runner import run_experiment


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_doctor(root: Path):
    checks = {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 11),
        "project_root": str(root),
        "agents": len(list((root / ".codex" / "agents").glob("*.toml"))),
        "skill_exists": (root / ".agents" / "skills" / "scientisttwo" / "SKILL.md").exists(),
        "problem_exists": (root / "research" / "problem.md").exists(),
        "budget_exists": (root / "research" / "budget.toml").exists(),
    }
    try:
        with (root / ".codex" / "config.toml").open("rb") as f:
            tomllib.load(f)
        for agent_file in (root / ".codex" / "agents").glob("*.toml"):
            with agent_file.open("rb") as f:
                tomllib.load(f)
        checks["codex_config_valid"] = True
    except Exception as exc:
        checks["codex_config_valid"] = False
        checks["codex_config_error"] = str(exc)
    try:
        with (root / "research" / "budget.toml").open("rb") as f:
            tomllib.load(f)
        checks["budget_valid"] = True
    except Exception as exc:
        checks["budget_valid"] = False
        checks["budget_error"] = str(exc)
    checks["ready"] = all([checks["python_ok"], checks["skill_exists"], checks["problem_exists"], checks["budget_exists"], checks["codex_config_valid"], checks["budget_valid"], checks["agents"] >= 27])
    _print(checks)
    if not checks["ready"]:
        raise SystemExit(1)


def build_parser():
    p = argparse.ArgumentParser(prog="st2", description="ScientistTwo-Codex research state and evidence controller")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check project scaffold and configuration")
    init = sub.add_parser("init", help="initialize persistent research state")
    init.add_argument("--problem", default="research/problem.md")
    sub.add_parser("status", help="show current research state")
    cand = sub.add_parser("candidate", help="candidate hypothesis operations")
    csub = cand.add_subparsers(dest="candidate_command", required=True)
    add = csub.add_parser("add")
    add.add_argument("--id", required=True)
    add.add_argument("--limitation", required=True)
    add.add_argument("--hypothesis", required=True)
    add.add_argument("--novelty", type=float)
    gate = sub.add_parser("gate", help="record a stage decision and advance the workflow")
    gate.add_argument("stage", choices=STAGES[:-2])
    gate.add_argument("--decision", required=True, choices=["accept", "refine", "reject", "bad", "good", "engineer"])
    gate.add_argument("--feedback", required=True)
    gate.add_argument("--score", type=float)
    gate.add_argument("--candidate", help="required for subset, full-set, and best-idea gates")
    gate.add_argument("--comparison", choices=["update_best", "keep_old"], help="required after ablation refinement; result_comparator's decision")
    exp = sub.add_parser("experiment", help="experiment runner")
    esub = exp.add_subparsers(dest="experiment_command", required=True)
    run = esub.add_parser("run")
    run.add_argument("--phase", required=True)
    run.add_argument("--candidate", required=True)
    run.add_argument("--command", dest="run_command", required=True, help="command string; executed without shell expansion")
    audit = sub.add_parser("audit", help="run four-part integrity audit")
    audit.add_argument("--manifest", default="research/audit/manifest.json")
    audit.add_argument("--online", action="store_true", help="verify DOI/arXiv records using public endpoints")
    return p


def main():
    args = build_parser().parse_args()
    try:
        root = repo_root()
        if args.command == "doctor":
            cmd_doctor(root)
        elif args.command == "init":
            _print(init_state(root, args.problem))
        elif args.command == "status":
            state = load_state(root)
            _print({"status": state.get("status"), "current_stage": state.get("current_stage"), "counters": state.get("counters"), "candidate_count": len(state.get("candidates", [])), "experiment_count": len(state.get("experiments", [])), "best_candidate_id": state.get("best_candidate_id"), "last_gate": state.get("gate_history", [])[-1] if state.get("gate_history") else None})
        elif args.command == "candidate":
            _print(add_candidate(root, args.id, args.limitation, args.hypothesis, args.novelty))
        elif args.command == "gate":
            _print({"current_stage": apply_gate(root, args.stage, args.decision, args.feedback, args.score, args.candidate, args.comparison)["current_stage"], "status": load_state(root)["status"]})
        elif args.command == "experiment":
            _print(run_experiment(root, args.phase, args.candidate, args.run_command))
        elif args.command == "audit":
            report = run_audit(root, args.manifest, args.online)
            _print(report)
            if report["overall"] != "PASS":
                raise SystemExit(2)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"st2: error: {exc}", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
