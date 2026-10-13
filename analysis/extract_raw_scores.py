"""Extract per-task raw execution scores from the benchmark run tree into one JSONL.

Source layout (private run tree; each run executed against a locally licensed
AspenTech PIMS installation, hence not redistributed as-is):

    <results_root>/benchmark_runs_V{v}/{model}_{condition}_V{v}/{task_id}/score.json
        (fallback: meta.json["score"], mirroring the scorer's own fallback)

Output: one JSON record per (model, condition, version, task):

    {"model", "condition", "version", "task", "src", "scores": {...}}

`scores` carries every metric emitted by the evaluator for that single run
(syntax, table_precision/recall/f1, row_recall, col_recall, match,
match_recall/precision, value_accuracy). All statistics reported in the paper
are recomputed from this file by `recompute_paper_stats.py`.

Usage:
    python extract_raw_scores.py <results_root> <out.jsonl>
"""
import json
import sys
from pathlib import Path

MODELS = ["deepseekpro", "deepseekflash", "gemma31b", "qwen27b"]
CONDS = [
    "baseline", "no_guidance", "doconly", "skill_base",
    "trace2skill", "skillopt", "skill_adaptive",
    "ablation_no_signal1", "ablation_no_signal2",
]
VERSIONS = [1, 2, 3, 4, 5]
METRIC_KEYS = [
    "syntax", "table_precision", "table_recall", "table_f1",
    "row_recall", "col_recall", "match", "match_recall",
    "match_precision", "value_accuracy",
]


def read_scores(task_dir: Path):
    """Return (scores_dict, source_name) or (None, None)."""
    sj = task_dir / "score.json"
    if sj.exists():
        try:
            d = json.loads(sj.read_text(encoding="utf-8"))
            if isinstance(d, dict) and d:
                return d, "score.json"
        except Exception:
            pass
    mj = task_dir / "meta.json"
    if mj.exists():
        try:
            d = json.loads(mj.read_text(encoding="utf-8"))
            sc = d.get("score")
            if isinstance(sc, dict) and sc:
                return sc, "meta.json"
            if any(k in d for k in METRIC_KEYS):
                return {k: d[k] for k in METRIC_KEYS if k in d}, "meta.json"
        except Exception:
            pass
    return None, None


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    n_rec = n_miss = 0
    per_cell = {}
    with out.open("w", encoding="utf-8") as f:
        for v in VERSIONS:
            for model in MODELS:
                for cond in CONDS:
                    run = root / f"benchmark_runs_V{v}" / f"{model}_{cond}_V{v}"
                    if not run.is_dir():
                        continue
                    k = 0
                    for td in sorted(run.iterdir()):
                        if not td.is_dir():
                            continue
                        scores, src = read_scores(td)
                        if scores is None:
                            n_miss += 1
                            continue
                        rec = {"model": model, "condition": cond, "version": v,
                               "task": td.name, "src": src, "scores": scores}
                        f.write(json.dumps(rec) + "\n")
                        n_rec += 1
                        k += 1
                    per_cell[f"{model}/{cond}/V{v}"] = k
    print(f"wrote {n_rec} records -> {out}")
    print(f"task dirs without any score: {n_miss}")
    print(f"run cells populated: {len(per_cell)}")
    sizes = sorted(set(per_cell.values()))
    print(f"records per run cell: {sizes}")


if __name__ == "__main__":
    main()
