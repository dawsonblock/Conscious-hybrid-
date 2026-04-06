"""Evaluation CLI for the hybrid cognitive agent."""

import argparse
from typing import Dict, Any

from hca.evaluation.harness_coordination import run as run_coordination
from hca.evaluation.harness_metacognition import run as run_metacognition
from hca.evaluation.harness_memory import run as run_memory
from hca.evaluation.harness_proactivity import run as run_proactivity
from hca.evaluation.harness_embodiment import run as run_embodiment
from hca.evaluation.harness_audit import run as run_audit
from hca.evaluation.metrics import compute_metrics


HARNESS_MAP = {
    "coordination": run_coordination,
    "metacognition": run_metacognition,
    "memory": run_memory,
    "proactivity": run_proactivity,
    "embodiment": run_embodiment,
    "audit": run_audit,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation harnesses for the hybrid cognitive agent.")
    parser.add_argument(
        "harness",
        nargs="?",
        default="coordination",
        choices=list(HARNESS_MAP.keys()),
        help="Which harness to run",
    )
    args = parser.parse_args()
    func = HARNESS_MAP[args.harness]
    result = func()
    metrics: Dict[str, Any] = compute_metrics(result)
    print(metrics)


if __name__ == "__main__":
    main()