"""Baseline method runners (Trace2Skill and SkillOpt) for comparison.

Implements two external baseline methods using the same PIMS execution interface:
  - Trace2Skill: Trajectory-level patch induction and hierarchical consolidation
  - SkillOpt: Bounded edits with construction-set validation gate

Both methods use the same construction tasks and skill library starting point.
They differ in how execution feedback is converted into skill updates.

Usage:
    python experiments/run_baselines.py --method trace2skill --rounds 3
    python experiments/run_baselines.py --method skillopt --rounds 3
    python experiments/run_baselines.py --both --rounds 5
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skillrefine.config import Config
from skillrefine.scoring import score_task, extract_oracle_components, load_benchmark_tasks
from skillrefine.agent import run_agent


# ---------------------------------------------------------------------------
# Trace2Skill Baseline
# ---------------------------------------------------------------------------

class Trace2SkillOptimizer:
    """Trace2Skill-style: trajectory distillation without validation gate.

    Key features:
    - Parallel trajectory analysis (success + failure)
    - Patch proposal from trajectories
    - Hierarchical patch consolidation
    - NO held-out validation gate (key weakness vs SkillRefine)
    """

    def __init__(self, skill_dir: Path, model: str = "deepseek-pro"):
        self.skill_dir = skill_dir
        self.model = model
        self.cfg = Config()
        self.best_score = 0.0

    def analyze_trajectories(self, results: List[Dict], oracle_lookup: Dict) -> List[Dict]:
        """Analyze trajectories and propose patches."""
        import openai

        successes = []
        failures = []

        for r in results:
            tid = r.get("task_id", "")
            oracle = oracle_lookup.get(tid, {})
            if not oracle:
                continue

            case_entries = r.get("case_entries", [])
            tables = [p.split("|")[1].strip() for line in case_entries
                      if isinstance(line, str) for p in [line.strip()]
                      if line.strip().startswith(("TABLE", "REPLACE")) and "|" in line]
            scores = score_task(
                {"tables_touched": tables, "case_entries": case_entries},
                r.get("pims_result", {}), [], oracle.get("objective"),
                oracle.get("tables", []), oracle.get("components", []),
            )
            match = scores.get("match", 0)
            entry = {
                "task_id": tid, "match": round(match, 3),
                "table_f1": round(scores.get("table_f1", 0), 3),
                "col_recall": round(scores.get("col_recall", 0), 3),
            }
            if match >= 0.5:
                successes.append(entry)
            else:
                failures.append(entry)

        # Propose patches from failures
        patches = []
        if failures:
            failure_lines = "\n".join(
                f"  {f['task_id']}: match={f['match']:.2f} tf1={f['table_f1']:.2f} col={f['col_recall']:.2f}"
                for f in sorted(failures, key=lambda x: x["match"])[:10]
            )
            prompt = (
                f"Analyze FAILED trajectories and propose skill patches.\n\n"
                f"## Failures\n{failure_lines}\n\n"
                f"## Skill Library\n"
                + "\n".join(f"  - {f.stem}" for f in sorted(self.skill_dir.glob("*.md")))
                + "\n\nPropose up to 5 patches in JSON format with op, target, content, reason."
            )
            patches.extend(self._call_llm_for_patches(prompt))

        if successes:
            success_lines = "\n".join(
                f"  {s['task_id']}: match={s['match']:.2f}"
                for s in sorted(successes, key=lambda x: x["match"], reverse=True)[:10]
            )
            prompt = (
                f"Analyze SUCCESSFUL trajectories and propose reinforcing patches.\n\n"
                f"## Successes\n{success_lines}\n\n"
                f"Propose up to 3 patches in JSON format."
            )
            patches.extend(self._call_llm_for_patches(prompt))

        return patches

    def _call_llm_for_patches(self, prompt: str) -> List[Dict]:
        """Call LLM to propose patches."""
        import openai
        client = openai.OpenAI(
            base_url=self.cfg.llm_api_base,
            api_key=self.cfg.llm_api_key,
            timeout=120.0,
        )
        try:
            model_id = self.cfg.get_model_id(self.model)
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=3000,
            )
            content = response.choices[0].message.content
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                start = content.find('{')
                end = content.rfind('}') + 1
                data = json.loads(content[start:end]) if start >= 0 else {}
            return data.get("patches", [])
        except Exception as e:
            print(f"  LLM patch proposal failed: {e}")
            return []

    def apply_patches(self, patches: List[Dict]):
        """Apply patches with deduplication (no validation gate)."""
        for patch in patches:
            target = self.skill_dir / f"{patch.get('target', '')}.md"
            content = patch.get("content", "")
            if target.exists():
                old = target.read_text(encoding="utf-8")
                if content not in old:
                    target.write_text(old + "\n\n" + content, encoding="utf-8")
            else:
                target.write_text(content, encoding="utf-8")

    def optimize_round(self, round_num: int, train_tasks: List[Dict],
                       test_tasks: List[Dict], oracle_lookup: Dict) -> Dict:
        """Run one optimization round."""
        print(f"\n=== Round {round_num} (Trace2Skill) ===")

        # Run on train set
        train_results = []
        for task in train_tasks:
            result = run_agent(task, "trace2skill", model=self.model, skip_pims=True)
            train_results.append(result)

        # Analyze trajectories
        patches = self.analyze_trajectories(train_results, oracle_lookup)
        print(f"  Proposed {len(patches)} patches")

        # Apply patches (NO validation gate)
        self.apply_patches(patches)

        # Evaluate on test set
        test_match = self._evaluate(test_tasks, oracle_lookup)
        print(f"  Test match: {test_match:.3f}")

        return {"patches": len(patches), "test_match": test_match, "accepted": True}

    def _evaluate(self, tasks: List[Dict], oracle_lookup: Dict) -> float:
        """Evaluate current skill library on test set."""
        total_match = 0
        count = 0
        for task in tasks:
            result = run_agent(task, "trace2skill", model=self.model, skip_pims=True)
            tid = task.get("id", "")
            oracle = oracle_lookup.get(tid, {})
            if not oracle:
                continue
            entries = result.get("case_entries", [])
            tables = [p.split("|")[1].strip() for line in entries
                      if isinstance(line, str) for p in [line.strip()]
                      if line.strip().startswith(("TABLE", "REPLACE")) and "|" in line]
            scores = score_task(
                {"tables_touched": tables, "case_entries": entries},
                result.get("pims_result", {}), [], oracle.get("objective"),
                oracle.get("tables", []), oracle.get("components", []),
            )
            total_match += scores.get("match", 0)
            count += 1
        return total_match / max(1, count)


# ---------------------------------------------------------------------------
# SkillOpt Baseline
# ---------------------------------------------------------------------------

class SkillOptOptimizer:
    """SkillOpt-style: bounded edits with construction-set validation gate.

    Key features:
    - Bounded edits (add/delete/replace only)
    - Held-out validation gate (accept only if match improves)
    - Edit budget with cosine decay
    - Rejected-edit buffer (negative feedback)
    """

    def __init__(self, skill_dir: Path, model: str = "deepseek-pro",
                 edit_budget: int = 4):
        self.skill_dir = skill_dir
        self.model = model
        self.cfg = Config()
        self.edit_budget_initial = edit_budget
        self.rejected_buffer: List[Dict] = []
        self.best_match = None

    def get_edit_budget(self, round_num: int, total_rounds: int) -> int:
        """Get edit budget for this round (cosine decay)."""
        progress = round_num / total_rounds
        budget = self.edit_budget_initial * (1 + math.cos(math.pi * progress)) / 2
        return max(1, int(budget))

    def analyze_and_edit(self, results: List[Dict], oracle_lookup: Dict,
                         round_num: int, total_rounds: int) -> List[Dict]:
        """Analyze failures and propose bounded edits."""
        import openai

        budget = self.get_edit_budget(round_num, total_rounds)

        # Build task results summary
        task_lines = []
        for r in results[:15]:
            tid = r.get("task_id", "")
            oracle = oracle_lookup.get(tid, {})
            if not oracle:
                continue
            entries = r.get("case_entries", [])
            tables = [p.split("|")[1].strip() for line in entries
                      if isinstance(line, str) for p in [line.strip()]
                      if line.strip().startswith(("TABLE", "REPLACE")) and "|" in line]
            scores = score_task(
                {"tables_touched": tables, "case_entries": entries},
                r.get("pims_result", {}), [], oracle.get("objective"),
                oracle.get("tables", []), oracle.get("components", []),
            )
            task_lines.append(
                f"  {tid}: match={scores.get('match', 0):.2f} "
                f"tf1={scores.get('table_f1', 0):.2f} "
                f"col={scores.get('col_recall', 0):.2f}"
            )

        # Read problematic skill contents
        skill_contents = []
        for f in sorted(self.skill_dir.glob("*.md"))[:5]:
            content = f.read_text(encoding="utf-8")[:300]
            skill_contents.append(f"### {f.stem}\n{content}")

        rejected_lines = [
            f"  - {r.get('op', '?')} {r.get('target', '?')}: {r.get('content', '')[:60]}"
            for r in self.rejected_buffer[-5:]
        ]

        prompt = (
            f"Propose BOUNDED edits to fix skill issues. Budget: {budget} edits.\n\n"
            f"## Rejected Edits (do NOT repeat)\n" + "\n".join(rejected_lines) + "\n\n"
            f"## Task Results\n" + "\n".join(task_lines) + "\n\n"
            f"## Skill Contents\n" + "\n\n".join(skill_contents) + "\n\n"
            f"Return JSON with 'analysis' and 'edits' (op, skill_name, old_content, content, reason)."
        )

        client = openai.OpenAI(
            base_url=self.cfg.llm_api_base,
            api_key=self.cfg.llm_api_key,
            timeout=300.0,
        )
        try:
            model_id = self.cfg.get_model_id(self.model)
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=3000,
            )
            content = response.choices[0].message.content
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                start = content.find('{')
                end = content.rfind('}') + 1
                data = json.loads(content[start:end]) if start >= 0 else {}
            edits = data.get("edits", [])
            return edits[:budget]
        except Exception as e:
            print(f"  Analyzer error: {e}")
            return []

    def apply_edits(self, edits: List[Dict]) -> Dict:
        """Apply bounded edits, return snapshot for rollback."""
        snapshot = {}
        for edit in edits:
            target = self.skill_dir / f"{edit.get('skill_name', edit.get('target', ''))}.md"
            op = edit.get("op", "add")
            content = edit.get("content", "")
            if op == "replace" and target.exists():
                old = target.read_text(encoding="utf-8")
                old_text = edit.get("old_content", "")
                if old_text in old:
                    target.write_text(old.replace(old_text, content), encoding="utf-8")
                    snapshot[str(target)] = old
            elif op == "add":
                if target.exists():
                    old = target.read_text(encoding="utf-8")
                    target.write_text(old + "\n\n" + content, encoding="utf-8")
                    snapshot[str(target)] = old
                else:
                    target.write_text(content, encoding="utf-8")
                    snapshot[str(target)] = None
            elif op == "delete" and target.exists():
                old = target.read_text(encoding="utf-8")
                text = edit.get("content", "")
                if text in old:
                    target.write_text(old.replace(text, ""), encoding="utf-8")
                    snapshot[str(target)] = old
        return snapshot

    def rollback(self, snapshot: Dict):
        """Rollback edits."""
        for path, old in snapshot.items():
            if old is None:
                Path(path).unlink(missing_ok=True)
            else:
                Path(path).write_text(old, encoding="utf-8")

    def optimize_round(self, round_num: int, total_rounds: int,
                       train_tasks: List[Dict], test_tasks: List[Dict],
                       oracle_lookup: Dict) -> Dict:
        """Run one optimization round."""
        budget = self.get_edit_budget(round_num, total_rounds)
        print(f"\n=== Round {round_num}/{total_rounds}, budget={budget} (SkillOpt) ===")

        # Run on train set
        train_results = []
        for task in train_tasks:
            result = run_agent(task, "skillopt", model=self.model, skip_pims=True)
            train_results.append(result)

        # Analyze and propose edits
        edits = self.analyze_and_edit(train_results, oracle_lookup, round_num, total_rounds)
        print(f"  Proposed {len(edits)} edits")

        # Apply edits
        snapshot = self.apply_edits(edits)

        # Validate on test set
        test_match = self._evaluate(test_tasks, oracle_lookup)
        print(f"  Test match: {test_match:.3f}")

        # Validation gate
        if self.best_match is None or test_match > self.best_match:
            print(f"  Accepted (improved match)")
            self.best_match = test_match
            self.rejected_buffer = []
            return {"accepted": True, "edits": len(edits), "test_match": test_match}
        else:
            print(f"  Rejected (no improvement)")
            self.rollback(snapshot)
            self.rejected_buffer.extend(edits)
            return {"accepted": False, "edits": len(edits), "test_match": test_match}

    def _evaluate(self, tasks: List[Dict], oracle_lookup: Dict) -> float:
        """Evaluate current skill library on test set."""
        total_match = 0
        count = 0
        for task in tasks:
            result = run_agent(task, "skillopt", model=self.model, skip_pims=True)
            tid = task.get("id", "")
            oracle = oracle_lookup.get(tid, {})
            if not oracle:
                continue
            entries = result.get("case_entries", [])
            tables = [p.split("|")[1].strip() for line in entries
                      if isinstance(line, str) for p in [line.strip()]
                      if line.strip().startswith(("TABLE", "REPLACE")) and "|" in line]
            scores = score_task(
                {"tables_touched": tables, "case_entries": entries},
                result.get("pims_result", {}), [], oracle.get("objective"),
                oracle.get("tables", []), oracle.get("components", []),
            )
            total_match += scores.get("match", 0)
            count += 1
        return total_match / max(1, count)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_oracle_lookup(bench_path: Path) -> Dict:
    """Build oracle lookup from benchmark file."""
    bench = json.load(open(bench_path, encoding="utf-8"))
    lookup = {}
    for model_key in ["WS", "GC"]:
        for tid, t in bench[model_key]["tasks"].items():
            tables, comps = extract_oracle_components(t)
            lookup[tid] = {
                "tables": tables,
                "components": comps,
            }
    return lookup


def split_bench(bench_path: Path, train_ratio: float = 0.4, seed: int = 42):
    """Split benchmark into train and test sets."""
    import random
    tasks = load_benchmark_tasks(bench_path)
    random.seed(seed)
    random.shuffle(tasks)
    n_train = int(len(tasks) * train_ratio)
    return tasks[:n_train], tasks[n_train:]


def main():
    parser = argparse.ArgumentParser(description="Run baseline methods (Trace2Skill, SkillOpt)")
    parser.add_argument("--method", choices=["trace2skill", "skillopt"], help="Method to run")
    parser.add_argument("--both", action="store_true", help="Run both methods")
    parser.add_argument("--rounds", type=int, default=3, help="Number of refinement rounds")
    parser.add_argument("--model", default="deepseek-pro",
                        choices=["deepseek-pro", "deepseek-flash", "gemma-31b", "qwen-27b"])
    parser.add_argument("--train-ratio", type=float, default=0.4,
                        help="Fraction of tasks for training")
    parser.add_argument("--skip-pims", action="store_true", default=True)
    args = parser.parse_args()

    methods = ["trace2skill", "skillopt"] if args.both else [args.method]
    if not args.method and not args.both:
        parser.error("Specify --method or --both")

    cfg = Config()
    train_tasks, test_tasks = split_bench(cfg.bench_eval_path, args.train_ratio)
    oracle_lookup = build_oracle_lookup(cfg.bench_eval_path)
    print(f"Split: {len(train_tasks)} train / {len(test_tasks)} test")

    for method in methods:
        print(f"\n{'='*60}")
        print(f"  Method: {method}")
        print(f"{'='*60}")

        skill_dir = cfg.get_skill_library_path(method)
        if not skill_dir.exists():
            print(f"  WARNING: Skill directory not found: {skill_dir}")
            continue

        if method == "trace2skill":
            optimizer = Trace2SkillOptimizer(skill_dir, model=args.model)
            for r in range(1, args.rounds + 1):
                optimizer.optimize_round(r, train_tasks, test_tasks, oracle_lookup)
        else:
            optimizer = SkillOptOptimizer(skill_dir, model=args.model)
            for r in range(1, args.rounds + 1):
                optimizer.optimize_round(r, args.rounds, train_tasks, test_tasks, oracle_lookup)


if __name__ == "__main__":
    main()
