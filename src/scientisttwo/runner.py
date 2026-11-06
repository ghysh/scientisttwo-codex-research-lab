from __future__ import annotations

import json
import os
import shlex
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import append_event, load_state, now, save_state


def git_commit(root: Path) -> str | None:
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def run_experiment(root: Path, phase: str, candidate: str, command: str) -> dict[str, Any]:
    argv = shlex.split(command, posix=True)
    if not argv:
        raise ValueError("Experiment command is empty.")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = root / "research" / "experiments" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    metrics_path = run_dir / "metrics.json"
    env = os.environ.copy()
    env.update({"ST2_RUN_ID": run_id, "ST2_RUN_DIR": str(run_dir), "ST2_METRICS_PATH": str(metrics_path)})
    started = now()
    proc = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, check=False)
    (run_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8")
    (run_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")
    metrics: dict[str, Any] | None = None
    metrics_error = None
    if metrics_path.exists():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if not isinstance(metrics, dict):
                raise ValueError("metrics.json must contain a JSON object")
        except Exception as exc:
            metrics_error = str(exc)
    else:
        metrics_error = "Command did not write metrics.json to ST2_METRICS_PATH"
    record = {
        "run_id": run_id,
        "phase": phase,
        "candidate_id": candidate,
        "command": argv,
        "started_at": started,
        "finished_at": now(),
        "return_code": proc.returncode,
        "git_commit": git_commit(root),
        "run_dir": str(run_dir.relative_to(root)),
        "metrics_file": str(metrics_path.relative_to(root)) if metrics_path.exists() else None,
        "metrics": metrics,
        "metrics_error": metrics_error,
    }
    (run_dir / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = load_state(root)
    state["experiments"].append(record)
    save_state(root, state)
    append_event(root, {"type": "experiment_run", **record})
    if proc.returncode != 0:
        raise RuntimeError(f"Experiment command failed (exit {proc.returncode}). See {run_dir / 'stderr.log'}")
    if metrics_error:
        raise RuntimeError(f"Experiment finished but metrics are missing/invalid: {metrics_error}. See {run_dir}")
    return record
