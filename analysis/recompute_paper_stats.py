"""Recompute every statistic reported in the paper from the released raw scores.

Data source: results/raw_scores.jsonl (one record per model x condition x
replicate x task; see analysis/extract_raw_scores.py for how it was produced
from the per-run score.json files).

Modes:
  verify       Recompute mean +/- within-task SD per (model, condition) for
               match / row_recall / col_recall and compare with paper Table 3.
  perlevel     Per-level (L1-L5) match F1 per (model, condition), plus the
               SkillRefine-Baseline gap averaged over backbones.
  significance Wilcoxon signed-rank + paired t-test on per-task 5-run mean
               match F1, SkillRefine vs each comparison condition, per backbone.
  all          All three (default).

Output is printed and saved to analysis/recomputed_results.json, then
automatically compared against analysis/expected_results.json (the reference
snapshot of the authors' original analysis run). Every reported number in the
paper can be independently verified by checking that the comparison prints
"ALL MATCH".

Provenance: direct adaptation of the authors' internal analysis driver; only
the data source changed (flat JSONL instead of the private per-run directory
tree). All aggregation and statistics code is unchanged.

Requirements: numpy, scipy.
Usage: python analysis/recompute_paper_stats.py [verify|perlevel|significance|all]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "results" / "raw_scores.jsonl"
OUT = HERE / "recomputed_results.json"
EXPECTED = HERE / "expected_results.json"

MODELS = ["deepseekpro", "deepseekflash", "gemma31b", "qwen27b"]
PAPER_MODEL_NAMES = {
    "deepseekpro": "DS-V4-Pro",
    "deepseekflash": "DS-V4-Flash",
    "gemma31b": "Gemma-4",
    "qwen27b": "Qwen-3.6",
}
CONDS = [
    "baseline", "no_guidance", "doconly", "skill_base",
    "trace2skill", "skillopt", "skill_adaptive",
    "ablation_no_signal1", "ablation_no_signal2",
]
VERSIONS = [1, 2, 3, 4, 5]
METRICS = ["match", "row_recall", "col_recall"]

# Paper Table 3 (tab:main-results): match F1 mean per model, KBS submission
PAPER_MATCH = {
    "baseline":       {"deepseekpro": .581, "deepseekflash": .618, "gemma31b": .620, "qwen27b": .468},
    "doconly":        {"deepseekpro": .620, "deepseekflash": .638, "gemma31b": .653, "qwen27b": .443},
    "skill_base":     {"deepseekpro": .694, "deepseekflash": .705, "gemma31b": .694, "qwen27b": .590},
    "trace2skill":    {"deepseekpro": .752, "deepseekflash": .698, "gemma31b": .771, "qwen27b": .656},
    "skillopt":       {"deepseekpro": .742, "deepseekflash": .719, "gemma31b": .778, "qwen27b": .711},
    "skill_adaptive": {"deepseekpro": .775, "deepseekflash": .757, "gemma31b": .800, "qwen27b": .764},
}

# ---- data source (flat JSONL of raw per-run scores) ----

_RECORDS = None


def load_records():
    global _RECORDS
    if _RECORDS is None:
        with RAW.open(encoding="utf-8") as f:
            _RECORDS = [json.loads(line) for line in f if line.strip()]
    return _RECORDS


def collect(model: str, cond: str, metric: str):
    """Return {task_id: [per-version scores]} for one model/condition/metric."""
    out = defaultdict(list)
    for r in load_records():
        if r["model"] != model or r["condition"] != cond:
            continue
        s = r.get("scores", {}).get(metric)
        if s is not None:
            out[r["task"]].append(float(s))
    return dict(out)


def task_means(data: dict):
    """{task_id: (mean over versions, sd over versions ddof=1, n_runs)}

    Only tasks scored in all 5 replicate runs are kept; stray directories
    with partial runs are reported once and excluded so that aggregates
    match the canonical 100 held-out tasks.
    """
    res = {}
    dropped = []
    for t, xs in data.items():
        if len(xs) != len(VERSIONS):
            dropped.append((t, len(xs)))
            continue
        arr = np.asarray(xs, dtype=float)
        sd = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        res[t] = (float(arr.mean()), sd, len(arr))
    if dropped and not getattr(task_means, "_warned", False):
        task_means._warned = True
        print(f"[note] dropping partially-run task dirs, e.g. {dropped[:6]} "
              f"(total {len(dropped)} in first cell seen)")
    return res


def level_of(task_id: str):
    parts = task_id.split("_")
    for p in parts:
        if p.startswith("L") and p[1:].isdigit():
            return int(p[1:])
    return None


def do_verify(results: dict):
    print("=" * 72)
    print("VERIFY: recomputed mean +/- avg within-task SD (paper values in parens)")
    print("=" * 72)
    verify = {}
    for cond in ["baseline", "no_guidance", "doconly", "skill_base",
                 "trace2skill", "skillopt", "skill_adaptive"]:
        verify[cond] = {}
        for model in MODELS:
            row = {}
            for metric in METRICS:
                tm = task_means(collect(model, cond, metric))
                if not tm:
                    row[metric] = None
                    continue
                means = np.array([v[0] for v in tm.values()])
                sds = np.array([v[1] for v in tm.values()])
                nruns = sorted({v[2] for v in tm.values()})
                row[metric] = {
                    "mean": round(float(means.mean()), 3),
                    "avg_sd": round(float(sds.mean()), 3),
                    "n_tasks": len(tm),
                    "n_runs": nruns,
                }
            verify[cond][model] = row
            m = row.get("match")
            paper = PAPER_MATCH.get(cond, {}).get(model)
            tag = ""
            if m and paper is not None:
                tag = f"  paper={paper:.3f}  diff={m['mean']-paper:+.3f}"
            print(f"{cond:>16} {PAPER_MODEL_NAMES[model]:>11}: "
                  f"m={m['mean'] if m else '?'}±{m['avg_sd'] if m else '?'} "
                  f"(n={m['n_tasks'] if m else 0}, runs={m['n_runs'] if m else []})"
                  f" rR={row['row_recall']['mean'] if row.get('row_recall') else '?'}"
                  f" cR={row['col_recall']['mean'] if row.get('col_recall') else '?'}"
                  f"{tag}")
    results["verify"] = verify


def do_perlevel(results: dict):
    print("=" * 72)
    print("PER-LEVEL match F1 (per-task 5-run means, averaged within level)")
    print("=" * 72)
    perlevel = {}
    conds = ["baseline", "doconly", "skill_base", "trace2skill", "skillopt",
             "skill_adaptive", "ablation_no_signal1", "ablation_no_signal2"]
    for cond in conds:
        perlevel[cond] = {}
        for model in MODELS:
            tm = task_means(collect(model, cond, "match"))
            by_level = defaultdict(list)
            for t, (mu, _sd, _n) in tm.items():
                lv = level_of(t)
                if lv:
                    by_level[lv].append(mu)
            perlevel[cond][model] = {
                str(lv): round(float(np.mean(v)), 3)
                for lv, v in sorted(by_level.items())
            }
    # Gap SkillRefine - Baseline averaged over the 4 backbones, per level
    gap = {}
    for lv in range(1, 6):
        diffs = []
        for model in MODELS:
            a = perlevel["skill_adaptive"][model].get(str(lv))
            b = perlevel["baseline"][model].get(str(lv))
            if a is not None and b is not None:
                diffs.append(a - b)
        gap[str(lv)] = round(float(np.mean(diffs)), 3) if diffs else None
    results["perlevel"] = perlevel
    results["perlevel_gap_skillrefine_minus_baseline"] = gap

    hdr = f"{'condition':>22} {'model':>11} " + " ".join(f"L{lv:>5}" for lv in range(1, 6))
    print(hdr)
    for cond in conds:
        for model in MODELS:
            vals = perlevel[cond][model]
            print(f"{cond:>22} {PAPER_MODEL_NAMES[model]:>11} "
                  + " ".join(f"{vals.get(str(lv), float('nan')):>6.3f}" for lv in range(1, 6)))
    print("\nAvg-across-backbones SkillRefine-Baseline gap per level (pp):")
    print("  " + "  ".join(f"L{lv}:{(gap[str(lv)] or 0)*100:+.1f}" for lv in range(1, 6)))


def rank_biserial(diffs: np.ndarray):
    """Compute W+, W-, and rank-biserial correlation r=(W+ - W-)/(W+ + W-)."""
    d = diffs[diffs != 0]
    n = len(d)
    if n == 0:
        return 0.0, 0.0, 0.0
    ranks = stats.rankdata(np.abs(d))
    w_plus = float(ranks[d > 0].sum())
    w_minus = float(ranks[d < 0].sum())
    r = (w_plus - w_minus) / (w_plus + w_minus) if (w_plus + w_minus) else 0.0
    return w_plus, w_minus, r


def do_significance(results: dict):
    print("=" * 72)
    print("SIGNIFICANCE: per-task 5-run mean match F1, SkillRefine vs each condition")
    print("(Wilcoxon signed-rank two-sided; r_rb = rank-biserial; d_z = paired Cohen's)")
    print("=" * 72)
    sig = {}
    comparisons = ["baseline", "doconly", "skill_base", "trace2skill", "skillopt"]
    for model in MODELS:
        a_tm = task_means(collect(model, "skill_adaptive", "match"))
        a = {t: v[0] for t, v in a_tm.items()}
        sig[model] = {}
        for cond in comparisons:
            b_tm = task_means(collect(model, cond, "match"))
            b = {t: v[0] for t, v in b_tm.items()}
            common = sorted(set(a) & set(b))
            diffs = np.array([a[t] - b[t] for t in common])
            entry = {
                "n_tasks": len(common),
                "mean_diff": round(float(diffs.mean()), 4) if len(diffs) else None,
            }
            nz = diffs[diffs != 0]
            if len(nz) < 6:
                entry.update({"wilcoxon_p": None, "note": "too few non-zero diffs"})
            else:
                try:
                    w = stats.wilcoxon(diffs, alternative="two-sided")
                    wp, wm, rrb = rank_biserial(diffs)
                    entry.update({
                        "wilcoxon_W": float(w.statistic),
                        "wilcoxon_p": float(w.pvalue),
                        "rank_biserial_r": round(rrb, 3),
                        "w_plus": wp, "w_minus": wm,
                    })
                except ValueError as e:
                    entry.update({"wilcoxon_p": None, "note": str(e)})
            if len(diffs) > 2 and diffs.std(ddof=1) > 0:
                t = stats.ttest_rel([a[t_] for t_ in common], [b[t_] for t_ in common])
                entry["ttest_p"] = float(t.pvalue)
                entry["cohen_dz"] = round(float(diffs.mean() / diffs.std(ddof=1)), 3)
            sig[model][cond] = entry
            p = entry.get("wilcoxon_p")
            ps = f"{p:.2e}" if p is not None else "n/a"
            print(f"{PAPER_MODEL_NAMES[model]:>11} vs {cond:>12}: n={entry['n_tasks']:>3} "
                  f"dM={entry.get('mean_diff')} W={entry.get('wilcoxon_W','-')} "
                  f"p={ps} r_rb={entry.get('rank_biserial_r','-')} "
                  f"d_z={entry.get('cohen_dz','-')}")
    results["significance"] = sig

    # Ablation check vs paper ranges:
    # paper: w/o compliance branch -0.011..-0.041 ; w/o match branch -0.016..-0.077
    print("\nABLATION means (match F1) for cross-check with paper ranges:")
    abl = {}
    for cond in ["skill_adaptive", "ablation_no_signal1", "ablation_no_signal2"]:
        abl[cond] = {}
        for model in MODELS:
            tm = task_means(collect(model, cond, "match"))
            mu = float(np.mean([v[0] for v in tm.values()])) if tm else None
            abl[cond][model] = round(mu, 3) if mu is not None else None
        print(f"  {cond:>22}: " + "  ".join(
            f"{PAPER_MODEL_NAMES[m]}={abl[cond][m]}" for m in MODELS))
    results["ablation_means"] = abl


def compare_with_expected(results: dict):
    """Deep-compare recomputed results against the shipped reference snapshot."""
    if not EXPECTED.exists():
        print("\n[compare] expected_results.json not found; comparison skipped")
        return None
    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    print("\n" + "=" * 72)
    print("COMPARISON vs expected_results.json (authors' original analysis run)")
    print("=" * 72)
    all_ok = True
    for k in exp:
        same = exp.get(k) == results.get(k)
        all_ok &= same
        print(f"  {k:>45}: {'MATCH' if same else '*** DIFF ***'}")
    extra = set(results) - set(exp)
    if extra:
        all_ok = False
        print(f"  extra keys not in expected: {sorted(extra)}")
    print(f"[compare] OVERALL: {'ALL MATCH' if all_ok else 'MISMATCH'}")
    return all_ok


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    results = {}
    if mode in ("verify", "all"):
        do_verify(results)
    if mode in ("perlevel", "all"):
        do_perlevel(results)
    if mode in ("significance", "all"):
        do_significance(results)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved -> {OUT}")
    if mode == "all":
        ok = compare_with_expected(results)
        if ok is False:
            sys.exit(2)


if __name__ == "__main__":
    main()
