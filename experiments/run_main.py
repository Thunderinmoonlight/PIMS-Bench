"""Main experiment runner for PIMS-Bench evaluation.

Runs all 6 conditions x 4 models on 100 held-out test tasks.
Each task is run n_runs times (default: 5) per paper:
  "mean and standard deviation computed over five independent executions"

Supports resume (checkpoint after each task-run).

Usage:
    # Single condition + model, 5 runs per task (paper default)
    python experiments/run_main.py --condition baseline --model deepseek-pro

    # Quick single-run test
    python experiments/run_main.py --condition baseline --n-runs 1

    # All conditions x all models, 5 runs
    python experiments/run_main.py --all-conditions --all-models

    # Specific tasks
    python experiments/run_main.py --condition baseline --tasks WS-L1-01 WS-L1-02
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skillrefine.agent import run_experiment
from skillrefine.config import Config


def main():
    parser = argparse.ArgumentParser(
        description="Run main PIMS-Bench experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Paper: "For each task, the mean and standard deviation are computed over
five independent executions and then averaged across the 100 held-out tasks."

Each backbone-condition pair = 100 tasks x 5 runs = 500 executions.
Total: 4 models x 6 conditions x 500 = 12,000 executions.
        """,
    )
    parser.add_argument(
        "--condition",
        choices=["baseline", "doconly", "skill_base", "skill_refined",
                 "trace2skill", "skillopt", "ablation_no_signal1", "ablation_no_signal2"],
        help="Experimental condition to run",
    )
    parser.add_argument(
        "--model",
        default="deepseek-pro",
        choices=["deepseek-pro", "deepseek-flash", "gemma-31b", "qwen-27b"],
        help="LLM model (default: deepseek-pro)",
    )
    parser.add_argument("--all-models", action="store_true", help="Run on all 4 models")
    parser.add_argument("--all-conditions", action="store_true", help="Run all 6 conditions")
    parser.add_argument("--tasks", nargs='+', help="Specific task IDs")
    parser.add_argument("--levels", nargs='+', type=int, help="Complexity levels (1-5)")
    parser.add_argument("--skip-pims", action="store_true", help="Skip PIMS execution")
    parser.add_argument(
        "--n-runs", type=int, default=5,
        help="Number of independent runs per task (default: 5, per paper)",
    )

    args = parser.parse_args()

    if not args.condition and not args.all_conditions:
        parser.error("Please specify --condition or --all-conditions")

    conditions = (
        ["baseline", "doconly", "skill_base", "skill_refined", "trace2skill", "skillopt"]
        if args.all_conditions
        else [args.condition]
    )

    models = (
        ["deepseek-pro", "deepseek-flash", "gemma-31b", "qwen-27b"]
        if args.all_models
        else [args.model]
    )

    cfg = Config()
    total_executions = len(conditions) * len(models) * 100 * args.n_runs

    print(f"{'='*70}")
    print(f"  PIMS-Bench Main Experiment")
    print(f"  Conditions: {', '.join(cfg.condition_display.get(c, c) for c in conditions)}")
    print(f"  Models:     {', '.join(cfg.get_model_id(m) for m in models)}")
    print(f"  Runs/task:  {args.n_runs}")
    print(f"  Total:      {len(conditions)} x {len(models)} x 100 x {args.n_runs} = {total_executions:,} executions")
    print(f"{'='*70}")

    start_time = time.time()

    for condition in conditions:
        for model in models:
            print(f"\n>>> {cfg.condition_display.get(condition, condition)} | {cfg.get_model_id(model)}")
            run_experiment(
                condition=condition,
                task_ids=args.tasks,
                levels=args.levels,
                model=model,
                skip_pims=args.skip_pims,
                n_runs=args.n_runs,
            )

    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"  Total time: {elapsed/3600:.1f} hours")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
