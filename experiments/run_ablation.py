"""Ablation study runner for PIMS-Bench.

Runs two ablation conditions to isolate the contribution of each signal:
  - ablation_no_signal1: Remove compliance filter (Stage 1), keep match decomposition only
  - ablation_no_signal2: Remove match decomposition (Stage 2), keep compliance filter only

Usage:
    python experiments/run_ablation.py --condition ablation_no_signal1 --model deepseek-pro
    python experiments/run_ablation.py --both --all-models
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skillrefine.config import Config
from skillrefine.scoring import load_benchmark_tasks
from skillrefine.agent import run_agent, run_experiment


def run_ablation(
    condition: str,
    model: str,
    task_ids: Optional[List[str]] = None,
    skip_pims: bool = False,
) -> List[Dict]:
    """Run ablation experiment.

    Args:
        condition: ablation_no_signal1 or ablation_no_signal2
        model: Model key
        task_ids: Optional specific task IDs
        skip_pims: Skip PIMS execution

    Returns:
        List of result dictionaries
    """
    if condition not in ("ablation_no_signal1", "ablation_no_signal2"):
        raise ValueError(f"Invalid ablation condition: {condition}")

    return run_experiment(
        condition=condition,
        task_ids=task_ids,
        model=model,
        skip_pims=skip_pims,
    )


def main():
    parser = argparse.ArgumentParser(description="Run ablation experiments")
    parser.add_argument(
        "--condition",
        choices=["ablation_no_signal1", "ablation_no_signal2"],
        help="Ablation condition to run",
    )
    parser.add_argument("--both", action="store_true", help="Run both ablation conditions")
    parser.add_argument(
        "--model", default="deepseek-pro",
        choices=["deepseek-pro", "deepseek-flash", "gemma-31b", "qwen-27b"],
    )
    parser.add_argument("--all-models", action="store_true")
    parser.add_argument("--tasks", nargs='+', help="Specific task IDs")
    parser.add_argument("--skip-pims", action="store_true")
    args = parser.parse_args()

    conditions = (
        ["ablation_no_signal1", "ablation_no_signal2"]
        if args.both
        else [args.condition]
    )
    models = (
        ["deepseek-pro", "deepseek-flash", "gemma-31b", "qwen-27b"]
        if args.all_models
        else [args.model]
    )

    if not args.condition and not args.both:
        parser.error("Specify --condition or --both")

    start = time.time()
    for cond in conditions:
        for model in models:
            run_ablation(cond, model, task_ids=args.tasks, skip_pims=args.skip_pims)

    print(f"\nTotal time: {(time.time() - start) / 3600:.1f} hours")


if __name__ == "__main__":
    main()
