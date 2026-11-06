"""Synthetic smoke test only. These numbers are not research evidence."""
import json
import os
from pathlib import Path

out = Path(os.environ["ST2_METRICS_PATH"])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({
    "metrics": {"synthetic_accuracy": 0.91, "synthetic_loss": 0.12},
    "seed": 123,
    "dataset_split": "SYNTHETIC_DEMO_NOT_A_BENCHMARK",
    "warning": "Synthetic smoke-test output; never cite as scientific evidence."
}, indent=2) + "\n", encoding="utf-8")
print("Wrote synthetic demo metrics to", out)
