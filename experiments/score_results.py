"""Scoring and reporting for PIMS-Bench experiments.

Unified scoring across all conditions and models.
Supports rescoring from raw case_entries.txt and cross-run aggregation.

Usage:
    python experiments/score_results.py --results-dir results/agent
    python experiments/score_results.py --results-dir results/benchmark_runs_V5 --detail
    python experiments/score_results.py --results-dir results/agent --latex
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skillrefine.config import Config
from skillrefine.scoring import score_task, extract_oracle_components, print_summary

METRICS = [
    "syntax", "table_f1", "table_precision", "table_recall",
    "row_recall", "col_recall", "match", "match_recall",
    "match_precision", "value_accuracy",
]

MODEL_LABELS = {
    "deepseek-pro": "DS-V4-Pro",
    "deepseek-flash": "DS-V4-Flash",
    "gemma-31b": "Gemma-4",
    "qwen-27b": "Qwen-3.6",
}

COND_DISPLAY = {
    "baseline": "Baseline",
    "doconly": "DocOnly",
    "skill_base": "SkillBase",
    "skill_refined": "SkillRefine",
    "trace2skill": "Trace2Skill",
    "skillopt": "SkillOpt",
    "ablation_no_signal1": "w/o Signal 1",
    "ablation_no_signal2": "w/o Signal 2",
}

COND_ORDER = [
    "baseline", "doconly", "skill_base",
    "trace2skill", "skillopt", "skill_refined",
    "ablation_no_signal1", "ablation_no_signal2",
]


def load_oracle_lookup(bench_path: Path) -> Dict:
    """Load oracle ground truth from benchmark file."""
    bench = json.load(open(bench_path, encoding="utf-8"))
    lookup = {}
    for model_key in ["WS", "GC"]:
        if model_key not in bench:
            continue
        for tid, t in bench[model_key]["tasks"].items():
            tables, components = extract_oracle_components(t)
            lookup[tid] = {
                "oracle_case": t.get("oracle_case", []),
                "oracle_tables": tables,
                "oracle_components": components,
            }
    return lookup


def score_from_result_dict(result: Dict, oracle: Dict) -> Dict:
    """Score a single result dictionary."""
    case_entries = result.get("case_entries", [])
    tables = []
    for e in case_entries:
        if isinstance(e, str) and e.upper().startswith("TABLE"):
            parts = [p.strip() for p in e.split("|")]
            if len(parts) >= 2:
                tables.append(parts[1])

    llm_plan = {"case_entries": case_entries, "tables_touched": list(set(tables))}
    pims_result = result.get("pims_result", {"status": None, "objective": None, "converged": False})

    return score_task(
        llm_plan, pims_result,
        oracle["oracle_case"], None,
        oracle["oracle_tables"], oracle["oracle_components"],
    )


def score_agent_results(results_dir: Path, bench_path: Path) -> Dict:
    """Score all agent result files in directory.

    Expected structure: results_dir/agent_{condition}_{model}.json
    """
    oracle_lookup = load_oracle_lookup(bench_path)
    all_scores = {}

    for json_file in sorted(results_dir.glob("agent_*.json")):
        # Parse filename: agent_{condition}_{model}.json
        stem = json_file.stem.replace("agent_", "")
        parts = stem.rsplit("_", 1)
        if len(parts) < 2:
            continue
        condition, model = parts[0], parts[1]

        data = json.load(open(json_file, encoding="utf-8"))
        cond_scores = []

        for r in data.get("results", []):
            tid = r.get("task_id", "")
            oracle = oracle_lookup.get(tid)
            if not oracle:
                continue
            score = score_from_result_dict(r, oracle)
            score["_task_id"] = tid
            cond_scores.append(score)

        key = f"{model}_{condition}"
        all_scores[key] = cond_scores
        print(f"  {key}: {len(cond_scores)} tasks scored")

    return all_scores


def print_compact_table(all_scores: Dict, metric: str = "match"):
    """Print compact summary table."""
    # Parse model/condition from keys
    models_seen = set()
    conditions_seen = set()
    data = {}
    se = {}

    for key, scores in all_scores.items():
        parts = key.split("_", 1)
        if len(parts) < 2:
            continue
        model, cond = parts

        models_seen.add(model)
        conditions_seen.add(cond)

        vals = [s.get(metric, 0) for s in scores]
        n = len(vals)
        mean = sum(vals) / n if n > 0 else 0
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / n) if n > 1 else 0
        sem = std / math.sqrt(n) if n > 0 else 0

        data[(model, cond)] = mean
        se[(model, cond)] = sem

    model_order = [m for m in MODEL_LABELS if m in models_seen]
    cond_order = [c for c in COND_ORDER if c in conditions_seen]
    for c in sorted(conditions_seen):
        if c not in cond_order:
            cond_order.append(c)

    # Print table
    cond_w = max(len(COND_DISPLAY.get(c, c)) for c in cond_order)
    header = f"{'Condition':<{cond_w}}"
    for m in model_order:
        header += f" {MODEL_LABELS.get(m, m):>16}"
    print(f"\n{'='*80}")
    print(f"  {metric.upper()} across models and conditions")
    print(f"{'='*80}")
    print(header)
    print("-" * len(header))

    for cond in cond_order:
        display = COND_DISPLAY.get(cond, cond)
        row = f"{display:<{cond_w}}"
        for m in model_order:
            val = data.get((m, cond))
            err = se.get((m, cond), 0)
            if val is not None:
                err_str = f"{err:.3f}".lstrip("0") or "0"
                row += f" {val:.3f}±{err_str:>6}"
            else:
                row += f" {'—':>16}"
        print(row)
    print(f"{'='*80}\n")


def print_latex_table(all_scores: Dict, metric: str = "match"):
    """Print LaTeX table matching paper format."""
    models_seen = set()
    conditions_seen = set()
    data = {}
    se = {}

    for key, scores in all_scores.items():
        parts = key.split("_", 1)
        if len(parts) < 2:
            continue
        model, cond = parts
        models_seen.add(model)
        conditions_seen.add(cond)

        vals = [s.get(metric, 0) for s in scores]
        n = len(vals)
        mean = sum(vals) / n if n > 0 else 0
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / n) if n > 1 else 0
        sem = std / math.sqrt(n) if n > 0 else 0

        data[(model, cond)] = mean
        se[(model, cond)] = sem

    model_order = [m for m in MODEL_LABELS if m in models_seen]
    cond_order = [c for c in COND_ORDER if c in conditions_seen]

    # Find best per model
    best = {}
    for m in model_order:
        col_vals = [(c, data.get((m, c), -1)) for c in cond_order]
        if col_vals:
            best[m] = max(col_vals, key=lambda x: x[1])[0]

    ncols = len(model_order)
    print(f"% === LaTeX Table: {metric} ===")
    print(r"\begin{table}[t]")
    print(r"\centering")
    print(r"\caption{Component match F1 across four LLM backbones and "
          + f"{len(cond_order)} conditions."
          + r" Values are mean $\pm$ SE. Best per model in \textbf{bold}.}")
    print(r"\label{tab:results}")
    print(r"\small")
    print(r"\setlength{\tabcolsep}{3pt}")
    print(r"\begin{tabular}{@{}l|" + "c" * ncols + r"@{}}")
    print(r"\toprule")

    header = r"\textbf{Condition}"
    for m in model_order:
        header += f" & \\textbf{{{MODEL_LABELS.get(m, m)}}}"
    header += r" \\"
    print(header)
    print(r"\midrule")

    LATEX_DISPLAY = {
        "baseline": r"\textsc{Baseline}",
        "doconly": r"\textsc{DocOnly}",
        "skill_base": r"\textsc{SkillBase}",
        "skill_refined": r"\textbf{\textsc{SkillRefine}}",
        "trace2skill": r"\textsc{Trace2Skill}",
        "skillopt": r"\textsc{SkillOpt}",
        "ablation_no_signal1": r"\textsc{w/o Sig.~1}",
        "ablation_no_signal2": r"\textsc{w/o Sig.~2}",
    }

    for cond in cond_order:
        display = LATEX_DISPLAY.get(cond, COND_DISPLAY.get(cond, cond))
        row = display
        for m in model_order:
            mean = data.get((m, cond), 0)
            sem_v = se.get((m, cond), 0)
            sem_str = f"{sem_v:.3f}".lstrip("0") or "0"
            if best.get(m) == cond:
                val_str = f"$\\mathbf{{{mean:.3f}}}_{{\\pm{sem_str}}}$"
            else:
                val_str = f"${mean:.3f}_{{\\pm{sem_str}}}$"
            row += f" & {val_str}"
        row += r" \\"
        print(row)

    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")


def main():
    parser = argparse.ArgumentParser(description="Score PIMS-Bench experiment results")
    parser.add_argument("--results-dir", type=str, default="results/agent",
                        help="Directory containing result files")
    parser.add_argument("--detail", action="store_true",
                        help="Show all 10 metrics")
    parser.add_argument("--latex", action="store_true",
                        help="Output LaTeX table")
    parser.add_argument("--metric", default="match",
                        choices=METRICS,
                        help="Primary metric for tables (default: match)")
    args = parser.parse_args()

    cfg = Config()
    results_dir = Path(args.results_dir)
    if not results_dir.is_absolute():
        results_dir = cfg.project_root / results_dir

    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        return

    print(f"Scoring results in: {results_dir}")
    all_scores = score_agent_results(results_dir, cfg.bench_eval_path)

    if not all_scores:
        print("No results found.")
        return

    if args.detail:
        # Per-condition detailed summary
        oracle_lookup = load_oracle_lookup(cfg.bench_eval_path)
        for key, scores in sorted(all_scores.items()):
            parts = key.split("_", 1)
            if len(parts) >= 2:
                model, cond = parts
                display = f"{COND_DISPLAY.get(cond, cond)} ({MODEL_LABELS.get(model, model)})"
            else:
                display = key
            results_with_scores = [{"scores": s} for s in scores]
            print_summary(results_with_scores, condition=display)
    else:
        print_compact_table(all_scores, metric=args.metric)

    if args.latex:
        print_latex_table(all_scores, metric=args.metric)


if __name__ == "__main__":
    main()
