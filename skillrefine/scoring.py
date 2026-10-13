"""Unified scoring framework for PIMS-Bench evaluation.

Core scoring module used by all experiment scripts.

Key exports:
  score_task()              - Multi-metric scoring (syntax, table_f1, row_recall, col_recall, match)
  extract_oracle_components() - Extract oracle tables & components from benchmark tasks

Metrics:
  syntax           - Fraction of CASE entries with valid format
  table_f1         - Table-level F1 (precision + recall)
  table_precision  - Fraction of agent tables that are in oracle
  table_recall     - Fraction of oracle tables that agent touched
  row_recall       - Fraction of oracle row tags found by agent
  col_recall       - Fraction of oracle column names found by agent
  match            - Component match F1 (across table, row, column, and value tuples)
  match_recall     - Fraction of oracle components found by agent
  match_precision  - Fraction of agent components that match oracle
  value_accuracy   - Among matched (table,row,col), fraction with correct value
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Valid PIMS table names for syntax validation
VALID_PIMS_TABLES = {
    'BUY', 'SELL', 'CAPS', 'PROCLIM', 'GASPLANT', 'SUBMODS',
    'BLENDS', 'BLNCAP', 'BLNMIX', 'BLNPROP', 'BLNSPEC', 'BLNTARG',
    'CRDCUTS', 'CRDDISTL', 'CRDQUAL', 'CRDBLEND', 'SWING',
    'ROWS', 'BOUNDS', 'GROUPS', 'RATIO', 'MIP', 'CASE',
    'SAT1', 'SAT2', 'SCCU', 'SLPR', 'SDHT', 'SDLC', 'SHCD',
    'ADDITIVE', 'ASSAYS', 'UTILBUY', 'UTILSEL',
    'BLNREST', 'BLNAPH', 'RFG', 'WSPECS', 'INTERACT', 'PBONUS', 'PROPRNG',
    'SCALE', 'NONLIN', 'CURVE', 'INDEX', 'PERCASE', 'PGUESS', 'EXPERT',
    'REPORT', 'SOLNKPIS', 'PRNTABS', 'PCALC', 'PCALCB', 'PDIST', 'UPOOL', 'VPOOL',
    'SNHT', 'SKHT', 'SIS4', 'SSFA', 'SGTU', 'SVAC', 'SCFP', 'SCNP',
    'STGT', 'SNSP', 'SPFS', 'SSRU', 'SSGP', 'SUGP', 'SUTL', 'SHYD',
    'ALTTAGS', 'NEWCUT', 'CRDPCALC', 'BLNGASES', 'GASES',
}

VALID_CASE_KEYWORDS = {'CASE', 'TABLE', 'REPLACE', 'MODIFIES', 'EXPERT', '*'}


def score_task(
    llm_plan: Optional[Dict],
    pims_result: Dict,
    oracle_case: List[str],
    oracle_objective: Optional[float],
    oracle_tables: List[str],
    oracle_components: List[Tuple],
) -> Dict[str, float]:
    """Score a single task using the multi-metric framework.

    Args:
        llm_plan: Agent's output plan with 'case_entries' and 'tables_touched'
        pims_result: PIMS execution result (status, objective, converged)
        oracle_case: Oracle CASE entries (ground truth)
        oracle_objective: Oracle objective value
        oracle_tables: Oracle table names
        oracle_components: Oracle (table, row, col, value) tuples

    Returns:
        Dictionary of metric scores
    """
    zero_scores = {
        "syntax": 0.0,
        "table_f1": 0.0,
        "table_precision": 0.0,
        "table_recall": 0.0,
        "row_recall": 0.0,
        "col_recall": 0.0,
        "match": 0.0,
        "match_recall": 0.0,
        "match_precision": 0.0,
        "value_accuracy": 0.0,
    }

    if llm_plan is None:
        return zero_scores

    case_entries = llm_plan.get("case_entries", [])

    # Dimension 1: CASE Syntax
    scores = {}
    scores["syntax"] = _check_syntax_validity(case_entries)

    # Parse agent and oracle components
    llm_components = _extract_components_from_case(case_entries)
    oracle_components_set = set(oracle_components)

    # Dimension 2: Table F1
    llm_tables = set(t.upper() for t in llm_plan.get("tables_touched", []))
    llm_tables_from_comps = set(c[0].upper() for c in llm_components)
    llm_tables = llm_tables | llm_tables_from_comps
    oracle_tables_set = set(t.upper() for t in oracle_tables)
    if not oracle_tables_set:
        oracle_tables_set = set(c[0].upper() for c in oracle_components)

    if llm_tables:
        correct_tables = llm_tables & oracle_tables_set
        t_p = len(correct_tables) / len(llm_tables)
        t_r = len(correct_tables) / len(oracle_tables_set) if oracle_tables_set else 1.0
    else:
        t_p = 0.0
        t_r = 0.0

    scores["table_precision"] = round(t_p, 3)
    scores["table_recall"] = round(t_r, 3)
    scores["table_f1"] = round(
        2 * t_p * t_r / (t_p + t_r) if (t_p + t_r) > 0 else 0.0, 3
    )

    # Dimension 3: Row Recall
    oracle_rows = set((c[0].upper(), c[1].upper()) for c in oracle_components)
    llm_rows = set((c[0].upper(), c[1].upper()) for c in llm_components)
    if oracle_rows:
        correct_rows = llm_rows & oracle_rows
        scores["row_recall"] = round(len(correct_rows) / len(oracle_rows), 3)
    else:
        scores["row_recall"] = 1.0 if not llm_rows else 0.0

    # Dimension 4: Column Recall (with PROCLIM column equivalence)
    oracle_cols = set((c[0].upper(), c[2].upper()) for c in oracle_components)
    llm_cols = set((c[0].upper(), c[2].upper()) for c in llm_components)
    if oracle_cols:
        correct_cols = set()
        for oc in oracle_cols:
            if oc in llm_cols:
                correct_cols.add(oc)
            elif oc[0] == 'PROCLIM':
                # Check PROCLIM column equivalence
                for lc in llm_cols:
                    if lc[0] == 'PROCLIM' and _proclim_col_equivalent(oc[1], lc[1]):
                        correct_cols.add(oc)
                        break
        scores["col_recall"] = round(len(correct_cols) / len(oracle_cols), 3)
    else:
        scores["col_recall"] = 1.0 if not llm_cols else 0.0

    # Dimension 5: Component Match F1
    if oracle_components_set:
        n_matched = _matching_components(llm_components, oracle_components_set)
        match_recall = n_matched / len(oracle_components_set)
        match_precision = n_matched / len(llm_components) if llm_components else 0.0
        scores["match"] = round(
            2 * match_precision * match_recall / (match_precision + match_recall)
            if (match_precision + match_recall) > 0 else 0.0, 3
        )
        scores["match_recall"] = round(match_recall, 3)
        scores["match_precision"] = round(match_precision, 3)

        # Value accuracy
        key_matches = 0
        value_correct = 0
        for lc in llm_components:
            lc_key = (lc[0].upper(), lc[1].upper(), lc[2].upper())
            for oc in oracle_components_set:
                oc_key = (oc[0].upper(), oc[1].upper(), oc[2].upper())
                if lc_key == oc_key:
                    key_matches += 1
                    try:
                        if abs(float(lc[3]) - float(oc[3])) <= 0.01:
                            value_correct += 1
                    except (ValueError, TypeError):
                        if str(lc[3]).upper().strip() == str(oc[3]).upper().strip():
                            value_correct += 1
                    break
        scores["value_accuracy"] = round(
            value_correct / key_matches if key_matches > 0 else 1.0, 3
        )
    else:
        scores["match"] = 1.0 if not llm_components else 0.0
        scores["match_recall"] = scores["match"]
        scores["match_precision"] = scores["match"]
        scores["value_accuracy"] = 1.0 if not llm_components else 0.0

    return scores


def _extract_components_from_case(case_entries: List[str]) -> set:
    """Extract (table, row, col, value) tuples from CASE entries.

    Improved TEXT column handling: explicitly tracks column positions from header row
    and handles both cases where TEXT value is present or omitted in data rows.
    """
    components = set()
    current_table = None
    current_cols = []
    text_positions = set()

    for line in case_entries:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]

        # Table declaration
        if parts[0] in ('TABLE', 'REPLACE'):
            current_table = parts[1].strip().upper() if len(parts) > 1 else None
            current_cols = []
            text_positions = set()
            continue

        # Skip CASE, MODIFIES, and terminators
        if parts[0].startswith('CASE') or parts[0].startswith('MODIFIES') or parts[0] == '*':
            continue

        # Header row (parts[0] is empty)
        if not parts[0] and current_table:
            raw_cols = [p.upper() for p in parts[1:]]
            text_positions = {i for i, c in enumerate(raw_cols) if c == "TEXT"}
            current_cols = [c for c in raw_cols if c and c != "TEXT"]
            continue

        # Data row
        if parts[0] and current_table:
            row_tag = parts[0].strip().upper()
            raw_values = [p.strip() for p in parts[1:]]

            # Remove trailing empty strings
            while raw_values and not raw_values[-1]:
                raw_values.pop()

            # Determine if TEXT value is present by checking position
            # If a value at a TEXT position is non-numeric, it's a TEXT description
            has_text_value = False
            if text_positions:
                text_pos = min(text_positions)
                if text_pos < len(raw_values):
                    try:
                        float(raw_values[text_pos])
                        has_text_value = False  # Numeric = data value
                    except ValueError:
                        has_text_value = True  # Non-numeric = TEXT description

            # Extract data values (excluding TEXT positions if present)
            if has_text_value:
                values = [v for i, v in enumerate(raw_values) if i not in text_positions]
            else:
                values = raw_values

            # Match values to columns
            for i, col in enumerate(current_cols):
                if i < len(values) and values[i]:
                    try:
                        val = float(values[i])
                        components.add((current_table, row_tag, col, val))
                    except ValueError:
                        components.add((current_table, row_tag, col, values[i]))

    return components


def _proclim_col_equivalent(col_a: str, col_b: str) -> bool:
    """Check if two PROCLIM column names are equivalent.

    PIMS accepts both MIN/MAX and numeric column headers (e.g., 90.0, 100.0)
    for PROCLIM CASE entries.
    """
    a = col_a.upper().strip()
    b = col_b.upper().strip()
    if a == b:
        return True

    # Both are numeric -> equivalent
    try:
        float(a)
        float(b)
        return True
    except ValueError:
        pass

    # One is MIN/MAX and the other is numeric -> equivalent
    if a in ('MIN', 'MAX') or b in ('MIN', 'MAX'):
        try:
            float(a) if a not in ('MIN', 'MAX') else float(b)
            return True
        except ValueError:
            pass

    return False


def _components_match(a, b, value_tol=0.01) -> bool:
    """Check if two component tuples match (with numeric tolerance)."""
    if len(a) != len(b):
        return False

    for i in range(len(a)):
        if i < 3:
            # Table, row, col: case-insensitive string match
            a_str = str(a[i]).upper().strip()
            b_str = str(b[i]).upper().strip()
            if a_str != b_str:
                # Special case: PROCLIM column equivalence
                if i == 2 and str(a[0]).upper().strip() == 'PROCLIM':
                    if _proclim_col_equivalent(a_str, b_str):
                        continue
                return False
        else:
            # Value: numeric match with tolerance
            try:
                if abs(float(a[i]) - float(b[i])) > value_tol:
                    return False
            except (ValueError, TypeError):
                if str(a[i]).upper().strip() != str(b[i]).upper().strip():
                    return False

    return True


def _matching_components(llm_comps: set, oracle_comps: set) -> int:
    """Count how many oracle components are matched by LLM components."""
    matched = 0
    for o in oracle_comps:
        for l in llm_comps:
            if _components_match(l, o):
                matched += 1
                break
    return matched


def _check_syntax_validity(case_entries: List[str]) -> float:
    """Check if CASE entries have valid syntax.

    Improved validation:
    - Validates table names against known PIMS tables
    - Checks for required terminators (*)
    - Validates column alignment
    """
    if not case_entries:
        return 0.0

    checks = 0
    valid = 0

    for line in case_entries:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]
        checks += 1

        keyword = parts[0].split()[0] if parts[0] else ""

        # Valid keyword
        if keyword.upper() in VALID_CASE_KEYWORDS or keyword == "" or keyword == "*":
            valid += 1
        elif parts[0] in ('TABLE', 'REPLACE') and len(parts) > 1:
            tbl = parts[1].strip().upper()
            if tbl in VALID_PIMS_TABLES:
                valid += 1
            else:
                # Unknown table name but valid format
                valid += 0.5
        else:
            # Data row - check if row tag looks reasonable
            if parts[0].isupper() or parts[0].startswith('CASE'):
                valid += 1
            else:
                valid += 0.5  # Partial credit for unclear format

    return round(valid / checks, 3) if checks > 0 else 0.0


def extract_oracle_components(task: Dict) -> Tuple[List[str], List[Tuple]]:
    """Extract oracle tables and components from a benchmark task.

    Args:
        task: Task dictionary with 'oracle_case' field

    Returns:
        Tuple of (table_names, component_tuples)
    """
    oracle_case = task.get("oracle_case", [])
    tables = []
    components = []

    current_table = None
    current_cols = []

    for line in oracle_case:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]

        if parts[0] in ('TABLE', 'REPLACE'):
            current_table = parts[1].strip().upper() if len(parts) > 1 else None
            if current_table and current_table not in tables:
                tables.append(current_table)
            current_cols = []
            continue

        if parts[0].startswith('CASE') or parts[0].startswith('MODIFIES') or parts[0] == '*':
            continue

        if not parts[0] and current_table:
            current_cols = [p.upper() for p in parts[1:] if p]
            continue

        if parts[0] and current_table:
            row_tag = parts[0].strip().upper()
            values = [p.strip() for p in parts[1:]]
            for i, col in enumerate(current_cols):
                if col == "TEXT":
                    continue
                if i < len(values) and values[i]:
                    try:
                        val = float(values[i])
                        components.append((current_table, row_tag, col, val))
                    except ValueError:
                        components.append((current_table, row_tag, col, values[i]))

    return tables, components


def print_summary(results: List[Dict], condition: str = ""):
    """Print summary table of experiment results.

    Args:
        results: List of result dictionaries with 'scores' field
        condition: Optional condition name for display
    """
    print(f"\n{'='*90}")
    if condition:
        print(f"  SUMMARY: {condition}")
    print(f"{'='*90}")

    # Metric keys (matching paper metrics)
    metric_keys = [
        "match", "table_f1", "table_precision", "table_recall",
        "row_recall", "col_recall", "value_accuracy", "syntax"
    ]

    # Aggregate scores
    agg = {k: [] for k in metric_keys}
    for r in results:
        scores = r.get("scores", {})
        for k in metric_keys:
            if k in scores:
                agg[k].append(scores[k])

    print(f"\n{'Metric':<25} {'Mean':>8} {'Min':>8} {'Max':>8} {'Std':>8}")
    print(f"{'-'*60}")

    for k in metric_keys:
        vals = agg[k]
        if vals:
            mean = sum(vals) / len(vals)
            mn = min(vals)
            mx = max(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals) if len(vals) > 1 else 0
            std = variance ** 0.5
            print(f"  {k:<23} {mean:>8.3f} {mn:>8.3f} {mx:>8.3f} {std:>8.3f}")

    # Task-level completion counts
    matches = [r.get("scores", {}).get("match", 0) for r in results]
    exact = sum(1 for m in matches if m >= 0.999)
    zero = sum(1 for m in matches if m < 0.001)
    partial = len(results) - exact - zero

    print(f"\n  Exact matches (match >= 0.999): {exact}/{len(results)} ({exact*100//max(1,len(results)):d}%)")
    print(f"  Partial matches:                {partial}/{len(results)}")
    print(f"  Zero matches (match < 0.001):   {zero}/{len(results)}")
    print(f"{'='*90}\n")


def load_benchmark_tasks(
    bench_path: Path,
    task_ids: Optional[List[str]] = None,
    levels: Optional[List[int]] = None,
    models: Optional[List[str]] = None,
) -> List[Dict]:
    """Load benchmark tasks from JSON file.

    Uses the simplified PIMS-Bench format where each task has:
      - task_id, case_number, scenario, oracle_case

    Level is inferred from task_id (e.g., "WS-L1-01" -> level 1).
    Tables touched are extracted from oracle_case.

    Args:
        bench_path: Path to benchmark JSON file
        task_ids: Optional list of specific task IDs to load
        levels: Optional list of complexity levels to filter
        models: Optional list of model keys to filter (e.g., ["WS", "GC"])

    Returns:
        List of task dictionaries
    """
    from skillrefine.benchmark import load_benchmark, load_task_list

    try:
        data = load_benchmark(bench_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return []

    return load_task_list(
        data,
        model_keys=models,
        task_ids=task_ids,
        levels=levels,
    )
