# PIMS-Bench & SkillRefine Artifacts

Data and code release accompanying the manuscript:

> **SkillRefine: Cross-source skill induction and execution-grounded
> refinement of agent knowledge libraries for industrial planning software**
> Dongxiao Liu, Boren Zhu, Yuwen Ding, Li Lei, Xiaoyong Li, Linghui Li (corresponding)
> *Knowledge-Based Systems* (under review)

## Contents

| Path | Description |
|---|---|
| `benchmark/` | PIMS-Bench task records: 40 construction-split and 100 held-out tasks over two PIMS demonstration scenarios (WS, GC) and five complexity levels (L1–L5). Each task carries a natural-language `scenario` and a structured `oracle_case` reference (table/row/column/value targets) used by the evaluator. |
| `skill_libraries/skill_base/` | **SkillBase** — the documentation-grounded initial library (Phase 1 output). |
| `skill_libraries/skill_refined/` | **SkillRefine** — the frozen library after execution-grounded refinement (Phases 2–4); this is the artifact evaluated in the paper. |
| `skill_libraries/skill_trace2skill/`, `skill_libraries/skill_skillopt/` | Frozen artifacts of the two external refinement baselines. |
| `skillrefine/` | Agent and evaluator implementation: PIMS COM client (`pims_client.py`), progressive skill loader (`skill_loader.py`), scorer (`scoring.py`), agent loop (`agent.py`), benchmark I/O (`benchmark.py`). |
| `experiments/` | Runners reproducing each evaluation condition: `run_main.py`, `run_baselines.py`, `run_ablation.py`, plus `score_results.py` and `verify_e2e.py`. |
| `results/raw_scores.jsonl` | Raw per-task execution scores underlying **all** reported statistics: 16,063 records = 4 backbones × 9 conditions × 5 replicates × 100 held-out tasks (partial cells dropped at aggregation time). Each record holds every metric emitted by the scorer for a single run. |
| `analysis/` | `extract_raw_scores.py` (how the JSONL was produced from per-run `score.json` files), `recompute_paper_stats.py` (recomputes every paper statistic), `expected_results.json` (reference snapshot of the authors' original analysis run). |

## Not included (non-redistributable)

- **AspenTech PIMS** — commercial software requiring a license from
  Aspen Technology, Inc. All experiments ran against PIMS v22.0.11 via its
  COM automation interface (`Pimswin.Document`) on Windows.
- **The Weight Sample / Gulf Coast demonstration models** shipped with PIMS.
- **The PIMS documentation set** (copyrighted).

Benchmark task records and oracle references were authored by us on top of
the demonstration scenarios; no model files or documentation content are
redistributed here.

## Verifying the paper's statistics

```bash
pip install numpy scipy
python analysis/recompute_paper_stats.py all
```

This recomputes, from `results/raw_scores.jsonl`:

- per-condition mean ± within-task SD for match F1 / row recall / column
  recall (paper Table 3),
- per-level (L1–L5) match F1 breakdowns,
- Wilcoxon signed-rank and paired t-tests, rank-biserial effects, and
  Cohen's d_z for SkillRefine vs. each comparison condition per backbone,
- ablation means for the two signal-removal conditions,

and automatically diffs the output against `analysis/expected_results.json`.
A final `OVERALL: ALL MATCH` confirms full reproduction.

## Re-running the benchmark

Requirements: Windows; a licensed AspenTech PIMS installation (v22.0.11 in
the paper) with the Weight Sample and Gulf Coast demonstration models
opened locally; Python 3.13; `pywin32`; access to an OpenAI-compatible LLM
endpoint. Copy `.env.example` to `.env`, fill in your endpoint/key and local
paths, then see the docstrings in `experiments/` for the per-condition
runners. Evaluation is fully automated: the agent operates PIMS through
COM, and the scorer compares the resulting database state against each
task's `oracle_case`.

## Terms of use

Provided for research reproducibility. The artifacts grant no rights to the
underlying commercial software; the benchmark scenarios are derived from
demonstration models of a licensed product and are intended for academic
use only. For questions, please open an issue in this repository or contact
the corresponding author (contact details are given in the manuscript).

## Citation

If you use these artifacts, please cite the paper above. A formal journal
reference (and archive DOI, if any) will be added here upon acceptance.
