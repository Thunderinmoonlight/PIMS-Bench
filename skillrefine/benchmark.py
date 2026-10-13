"""Benchmark data loading and validation for PIMS-Bench.

PIMS-Bench uses a minimal JSON format with four required fields per task:
  - task_id: unique identifier (e.g., "WS-L1-01")
  - case_number: PIMS CASE number for execution
  - scenario: English business scenario
  - oracle_case: ground truth CASE entries (pipe-delimited)

All other metadata (level, tables_touched, model key) is derived from
the task_id and oracle_case.

Usage::

    from skillrefine.benchmark import load_benchmark, load_task_list

    data = load_benchmark(Path("data/benchmarks/bench_eval.json"))
    tasks = load_task_list(data, model_keys=["WS"], levels=[1, 2])
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Required fields per task
REQUIRED_TASK_FIELDS = {"task_id", "case_number", "scenario", "oracle_case"}

# Valid model keys
VALID_MODEL_KEYS = {"WS", "GC"}


def load_benchmark(path: Path) -> Dict[str, Any]:
    """Load benchmark data from a JSON file.

    Args:
        path: Path to benchmark JSON file.

    Returns:
        Benchmark data dictionary with model keys ("WS", "GC").

    Raises:
        FileNotFoundError: If benchmark file does not exist.
        ValueError: If benchmark format is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    validate_benchmark_format(data)
    return data


def validate_benchmark_format(data: Dict[str, Any]) -> bool:
    """Validate that benchmark data conforms to the minimal schema.

    Expected structure::

        {
            "WS": {
                "tasks": {
                    "WS-L1-01": {
                        "task_id": "WS-L1-01",
                        "case_number": 500,
                        "scenario": "...",
                        "oracle_case": [...]
                    }
                }
            },
            "GC": { "tasks": { ... } }
        }

    Args:
        data: Benchmark dictionary to validate.

    Returns:
        True if valid.

    Raises:
        ValueError: If format is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Benchmark root must be a dict")

    for model_key in data:
        if model_key not in VALID_MODEL_KEYS:
            # Allow extra keys but warn
            continue

        model_data = data[model_key]
        if not isinstance(model_data, dict):
            raise ValueError(f"Model '{model_key}' must be a dict")

        if "tasks" not in model_data:
            raise ValueError(f"Model '{model_key}' missing 'tasks' key")

        tasks = model_data["tasks"]
        if not isinstance(tasks, dict):
            raise ValueError(f"Model '{model_key}' tasks must be a dict")

        for task_id, task_data in tasks.items():
            if not isinstance(task_data, dict):
                raise ValueError(f"Task '{task_id}' must be a dict")

            missing = REQUIRED_TASK_FIELDS - set(task_data.keys())
            if missing:
                raise ValueError(
                    f"Task '{task_id}' missing required fields: {missing}"
                )

            if not isinstance(task_data["oracle_case"], list):
                raise ValueError(
                    f"Task '{task_id}': oracle_case must be a list"
                )

            if not isinstance(task_data["case_number"], (int, float)):
                raise ValueError(
                    f"Task '{task_id}': case_number must be numeric"
                )

    return True


def infer_level(task_id: str) -> int:
    """Infer complexity level from task ID.

    Args:
        task_id: Task identifier (e.g., "WS-L1-01", "GC-T3-05")

    Returns:
        Complexity level (1-5), or 0 if cannot be inferred.
    """
    match = re.search(r"L(\d)", task_id, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"T(\d)", task_id, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def infer_model_key(task_id: str) -> str:
    """Infer model key from task ID prefix.

    Args:
        task_id: Task identifier (e.g., "WS-L1-01")

    Returns:
        Model key ("WS" or "GC"), or empty string if unknown.
    """
    for key in VALID_MODEL_KEYS:
        if task_id.upper().startswith(key + "-"):
            return key
    return ""


def extract_tables_from_oracle(oracle_case: List[str]) -> List[str]:
    """Extract table names from oracle CASE entries.

    Args:
        oracle_case: List of CASE entry strings.

    Returns:
        List of unique table names (uppercase).
    """
    tables = []
    for line in oracle_case:
        if not isinstance(line, str):
            continue
        parts = [p.strip() for p in line.split("|")]
        if parts[0] in ("TABLE", "REPLACE") and len(parts) > 1:
            tbl = parts[1].strip().upper()
            if tbl and tbl not in tables:
                tables.append(tbl)
    return tables


def load_task_list(
    data: Dict[str, Any],
    model_keys: Optional[List[str]] = None,
    task_ids: Optional[List[str]] = None,
    levels: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """Extract a flat list of tasks from benchmark data.

    Each task is enriched with derived fields:
      - level: inferred from task_id
      - model: inferred from task_id prefix
      - tables_touched: extracted from oracle_case

    Args:
        data: Benchmark data dictionary.
        model_keys: Optional filter for model keys (e.g., ["WS"]).
        task_ids: Optional filter for specific task IDs.
        levels: Optional filter for complexity levels.

    Returns:
        List of task dictionaries ready for experiment execution.
    """
    tasks: List[Dict[str, Any]] = []

    for mk in data:
        if model_keys and mk not in model_keys:
            continue
        if mk not in VALID_MODEL_KEYS:
            continue

        model_tasks = data[mk].get("tasks", {})

        for tid, tdata in model_tasks.items():
            level = infer_level(tid)

            # Apply filters
            if task_ids and tid not in task_ids:
                continue
            if levels and level not in levels:
                continue

            oracle_case = tdata.get("oracle_case", [])
            tables_touched = extract_tables_from_oracle(oracle_case)

            task = {
                "id": tid,
                "task_id": tid,
                "model": mk,
                "level": level,
                "case_number": tdata["case_number"],
                "scenario": tdata.get("scenario", ""),
                "scenario": tdata.get("scenario", ""),
                "tables_touched": tables_touched,
                "oracle_case": oracle_case,
            }
            tasks.append(task)

    return tasks


def get_benchmark_stats(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute summary statistics for a benchmark dataset.

    Args:
        data: Benchmark data dictionary.

    Returns:
        Dictionary with per-model and overall statistics.
    """
    stats: Dict[str, Any] = {}
    total = 0

    for mk in sorted(data.keys()):
        if mk not in VALID_MODEL_KEYS:
            continue
        model_tasks = data[mk].get("tasks", {})
        level_counts: Dict[int, int] = {}
        for tid, tdata in model_tasks.items():
            level = infer_level(tid)
            level_counts[level] = level_counts.get(level, 0) + 1

        stats[mk] = {
            "task_count": len(model_tasks),
            "level_distribution": dict(sorted(level_counts.items())),
        }
        total += len(model_tasks)

    stats["total"] = total
    return stats


def save_benchmark(data: Dict[str, Any], path: Path) -> None:
    """Save benchmark data to a JSON file.

    Args:
        data: Benchmark data dictionary.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
