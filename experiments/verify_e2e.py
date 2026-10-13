"""End-to-end verification on a single benchmark task.

Runs the full pipeline: Agent -> CASE entries -> Excel write -> PIMS COM -> Signals -> Restore.
Useful for debugging and verifying the complete workflow.

Usage:
    python experiments/verify_e2e.py --task-id WS-L1-05
    python experiments/verify_e2e.py --task-id GC-L1-03 --model deepseek-flash
    python experiments/verify_e2e.py --task-id WS-L1-05 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skillrefine.config import Config
from skillrefine.scoring import extract_oracle_components, score_task
from skillrefine.agent import run_agent


def kill_pims():
    """Force kill PIMS and Excel processes."""
    for proc in ["PIMSWIN.EXE", "EXCEL.EXE"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, timeout=10)
        except Exception:
            pass
    time.sleep(2)


def write_case_xlwt(xls_path: str, case_num: int, case_entries: list) -> bool:
    """Write CASE entries to Excel Case sheet using xlrd/xlwt."""
    try:
        import xlrd
        from xlutils.copy import copy as xlcopy

        rb = xlrd.open_workbook(xls_path, formatting_info=True)
        wb = xlcopy(rb)

        sheet_idx = None
        for i, name in enumerate(rb.sheet_names()):
            if name.lower() == "case":
                sheet_idx = i
                break
        if sheet_idx is None:
            print("  ERROR: Case sheet not found")
            return False

        ws = wb.get_sheet(sheet_idx)
        rs = rb.sheet_by_index(sheet_idx)
        insert_row = rs.nrows

        ws.write(insert_row, 0, f"CASE {case_num}")
        insert_row += 1

        for entry in case_entries:
            if not isinstance(entry, str):
                continue
            parts = [p.strip() for p in entry.split("|")]
            if entry.strip().startswith("CASE"):
                continue
            elif entry.strip().startswith(("TABLE", "REPLACE")):
                ws.write(insert_row, 0, parts[0])
                if len(parts) > 1:
                    ws.write(insert_row, 1, parts[1])
            elif entry.strip() == "*":
                ws.write(insert_row, 0, "*")
            elif parts[0] == "":
                for j, p in enumerate(parts[1:], start=1):
                    if p:
                        ws.write(insert_row, j, p)
            else:
                for j, p in enumerate(parts):
                    if p:
                        try:
                            ws.write(insert_row, j, float(p))
                        except ValueError:
                            ws.write(insert_row, j, p)
            insert_row += 1

        wb.save(xls_path)
        return True
    except Exception as e:
        print(f"  Write error: {e}")
        return False


def run_pims_case(model_dir: str, xls_path: str, case_num: int, model_key: str = "WS") -> Dict:
    """Run PIMS case via COM automation."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "skillrefine"))
        from pims_client import AspenPIMS

        pims = AspenPIMS(suppress_ui=True)
        pims.open_model(model_dir)

        base_tables = ["CASE", "BUY", "SELL", "CAPS"]
        for tbl in base_tables:
            sheet = {"CASE": "Case", "BUY": "Buy", "SELL": "Sell", "CAPS": "Caps"}.get(tbl, tbl)
            try:
                pims.set_table_file(tbl, 0, xls_path, sheet)
            except Exception:
                pass

        pims.set_cases(f"001,{case_num:03d}")
        pims.run_model(False)
        time.sleep(2)

        pims.set_case_number(case_num)
        obj = float(pims.get_objective_value())
        status = pims.get_solution_status()
        converged = "CONVERGED" in status.upper() or "OPTIMAL" in status.upper()

        pims.close_model()
        pims.close_pims()

        return {"converged": converged, "objective": round(obj, 4), "status": status}
    except Exception as e:
        try:
            pims.close_model()
            pims.close_pims()
        except Exception:
            pass
        return {"converged": False, "objective": None, "status": str(e), "error": str(e)}


def verify_e2e(task_id: str, model: str = "deepseek-pro",
               condition: str = "skill_base", dry_run: bool = False):
    """Run full end-to-end verification on one task."""
    cfg = Config()
    start_time = time.time()
    log_lines = []

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}"
        print(line)
        log_lines.append(line)

    log(f"{'='*60}")
    log(f"E2E Verification: {task_id}")
    log(f"Model: {model}, Condition: {condition}, Dry-run: {dry_run}")
    log(f"{'='*60}")

    # Load benchmark
    bench = json.load(open(cfg.bench_eval_path, encoding="utf-8"))
    task_data = None
    model_key = None
    for mk in ["WS", "GC"]:
        if mk in bench and task_id in bench[mk]["tasks"]:
            task_data = bench[mk]["tasks"][task_id]
            model_key = mk
            break

    if task_data is None:
        log(f"ERROR: Task {task_id} not found")
        return None

    # case_number is now a direct field in the task
    case_num = task_data.get("case_number", 0)
    model_cfg = cfg.model_paths[model_key]
    xls_path = model_cfg["xls_path"]
    model_dir = model_cfg["model_dir"]

    oracle_tables, oracle_comps = extract_oracle_components(task_data)
    # Derive tables_touched from oracle_case
    tables_touched = oracle_tables

    # Infer level from task_id
    import re
    level_match = re.search(r"L(\d)", task_id)
    level = int(level_match.group(1)) if level_match else 1

    log(f"  Model: {model_key}, Case#: {case_num}, Level: {level}")
    log(f"  Tables: {tables_touched}")

    # Backup Excel
    backup = xls_path + ".bak_e2e"
    log("Backing up Excel...")
    shutil.copy2(xls_path, backup)
    report = None

    try:
        # Kill residual processes
        kill_pims()

        # Run agent (skip_pims=True: agent only generates CASE entries)
        log("Running agent...")
        agent_task = {
            "id": task_id,
            "model": model_key,
            "level": level,
            "scenario": task_data.get("scenario", ""),
            "tables_touched": tables_touched,
            "oracle_case": task_data.get("oracle_case", []),
        }
        result = run_agent(agent_task, condition, model=model, skip_pims=True)

        entries = result.get("case_entries", [])
        flat = []
        for block in entries:
            if isinstance(block, list):
                flat.extend(block)
            elif isinstance(block, str):
                flat.append(block)

        log(f"  Agent: {result.get('steps', 0)} steps, {len(flat)} CASE lines")
        for line in flat[:15]:
            log(f"    | {line}")

        # Write CASE to Excel
        write_ok = False
        if case_num > 0 and flat and not dry_run:
            log("Writing CASE to Excel...")
            write_ok = write_case_xlwt(xls_path, case_num, flat)
            log(f"  Write: {'OK' if write_ok else 'FAIL'}")

        # Run PIMS
        pims_result = {"converged": False, "objective": None, "status": "skipped"}
        if write_ok and case_num > 0 and not dry_run:
            kill_pims()
            log("Running PIMS...")
            pims_result = run_pims_case(model_dir, xls_path, case_num, model_key)
            log(f"  PIMS: converged={pims_result.get('converged')}, obj={pims_result.get('objective')}")

        # Compute signals
        tables = [p.split("|")[1].strip() for line in flat
                  if isinstance(line, str) for p in [line.strip()]
                  if line.strip().startswith(("TABLE", "REPLACE")) and "|" in line]
        scores = score_task(
            {"tables_touched": tables, "case_entries": flat},
            pims_result, task_data.get("oracle_case", []),
            None, oracle_tables, oracle_comps,
        )

        log(f"  Scores: match={scores.get('match', 0):.3f} "
            f"tf1={scores.get('table_f1', 0):.3f} "
            f"row={scores.get('row_recall', 0):.3f} "
            f"col={scores.get('col_recall', 0):.3f}")

        # Build report
        elapsed = time.time() - start_time
        report = {
            "task_id": task_id,
            "model_key": model_key,
            "case_num": case_num,
            "agent": {
                "condition": condition,
                "model": model,
                "steps": result.get("steps", 0),
                "case_entries": flat,
            },
            "excel_write": {"success": write_ok},
            "pims": pims_result,
            "scores": scores,
            "elapsed_seconds": round(elapsed, 1),
            "log": log_lines,
        }

        return report

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"task_id": task_id, "error": str(e), "log": log_lines}

    finally:
        # Restore Excel
        log("Restoring Excel...")
        if os.path.exists(backup):
            try:
                shutil.copy2(backup, xls_path)
                os.remove(backup)
                log("  Excel restored")
            except Exception as e:
                log(f"  Restore error: {e}")
        kill_pims()

        elapsed = time.time() - start_time
        log(f"Verification complete. Time: {elapsed:.1f}s")

        if report is not None:
            output_dir = cfg.results_dir / "e2e_verify"
            output_dir.mkdir(parents=True, exist_ok=True)
            report_path = output_dir / "verify_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            log(f"Report saved to {report_path}")


def main():
    parser = argparse.ArgumentParser(description="End-to-end verification")
    parser.add_argument("--task-id", default="WS-L1-05", help="Task ID")
    parser.add_argument("--model", default="deepseek-pro",
                        choices=["deepseek-pro", "deepseek-flash", "gemma-31b", "qwen-27b"])
    parser.add_argument("--condition", default="skill_base")
    parser.add_argument("--dry-run", action="store_true", help="Skip PIMS execution")
    args = parser.parse_args()

    verify_e2e(args.task_id, args.model, args.condition, args.dry_run)


if __name__ == "__main__":
    main()
