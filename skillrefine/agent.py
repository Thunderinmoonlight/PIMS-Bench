"""Tool-calling agent runner for PIMS-Bench evaluation.

This module implements an autonomous agent that operates PIMS (Process Industry
Modeling System) through OpenAI-compatible function calling. The agent discovers
table structures, writes CASE modifications, and verifies results via PIMS execution.

Experimental conditions control which tools are available:
  - baseline: read/write Excel + run PIMS only
  - doconly: + read raw documentation
  - skill_base: + read unrefined skills
  - skill_refined: + read refined skills (SkillRefine method)
  - trace2skill/skillopt: baseline skill methods

Usage:
    from skillrefine.agent import run_agent, run_experiment
    result = run_agent(task, condition="baseline", model="deepseek-pro")
    results = run_experiment(condition="skill_refined", levels=[1, 2])
"""
from __future__ import annotations

import gc
import json
import logging
import os
import shutil
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from skillrefine.config import Config, get_config

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions (OpenAI Function Calling Format)
# =============================================================================

TOOL_LIST_SHEETS = {
    "type": "function",
    "function": {
        "name": "list_sheets",
        "description": (
            "List all sheet (table) names in the PIMS Excel workbook. "
            "Use this first to discover what tables exist."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

TOOL_READ_SHEET = {
    "type": "function",
    "function": {
        "name": "read_sheet",
        "description": (
            "Read a sheet's structure: headers (row 3) and data rows "
            "(col A = row tag, col B = text, rest = values). Returns up to 30 rows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {
                    "type": "string",
                    "description": "Sheet name (e.g., 'Buy', 'Sell', 'Caps')",
                }
            },
            "required": ["sheet_name"],
        },
    },
}

TOOL_READ_CELL = {
    "type": "function",
    "function": {
        "name": "read_cell",
        "description": (
            "Read a specific cell value by sheet name, row tag (column A), "
            "and column header."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {"type": "string"},
                "row_tag": {
                    "type": "string",
                    "description": "Row identifier in column A (e.g., 'JET', 'KUW', 'CCCU')",
                },
                "col_header": {
                    "type": "string",
                    "description": "Column header name (e.g., 'MAX', 'PRICE', 'COST')",
                },
            },
            "required": ["sheet_name", "row_tag", "col_header"],
        },
    },
}

TOOL_WRITE_CASE = {
    "type": "function",
    "function": {
        "name": "write_case",
        "description": (
            "Write CASE table entries to the Case sheet. These modifications "
            "will be applied when PIMS runs. Format each entry as a string line. End with '*'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "case_number": {
                    "type": "integer",
                    "description": "CASE number (e.g., 101)",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable case description",
                },
                "entries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "CASE table lines. Example: "
                        "['TABLE | SELL', ' | TEXT | PRICE |', 'JET | Kero/Jet | 150.0 |', '*']"
                    ),
                },
            },
            "required": ["case_number", "description", "entries"],
        },
    },
}

TOOL_RUN_PIMS = {
    "type": "function",
    "function": {
        "name": "run_pims",
        "description": (
            "Run PIMS with the specified CASE numbers. "
            "Returns solution status and objective value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "case_numbers": {
                    "type": "string",
                    "description": "Case numbers to run, e.g., '001,101' or '001,101,102'",
                },
            },
            "required": ["case_numbers"],
        },
    },
}

TOOL_READ_DOC = {
    "type": "function",
    "function": {
        "name": "read_doc",
        "description": (
            "Read PIMS documentation for a specific table. "
            "Returns column definitions, usage rules, and constraints."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Table name (e.g., 'BUY', 'SELL', 'CAPS')",
                },
            },
            "required": ["table_name"],
        },
    },
}

TOOL_READ_SKILL = {
    "type": "function",
    "function": {
        "name": "read_skill",
        "description": (
            "Read a compiled skill document containing structured table schemas, "
            "column constraints, and operation rules."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill/table name (e.g., 'BUY', 'SELL', 'CAPS', 'BLENDS')",
                },
            },
            "required": ["skill_name"],
        },
    },
}

# Map tool names to definitions for dynamic lookup
TOOL_REGISTRY: Dict[str, Dict] = {
    "list_sheets": TOOL_LIST_SHEETS,
    "read_sheet": TOOL_READ_SHEET,
    "read_cell": TOOL_READ_CELL,
    "write_case": TOOL_WRITE_CASE,
    "run_pims": TOOL_RUN_PIMS,
    "read_doc": TOOL_READ_DOC,
    "read_skill": TOOL_READ_SKILL,
}


def get_tools_for_condition(condition: str, cfg: Config) -> List[Dict]:
    """Get tool definitions for an experimental condition.

    Args:
        condition: Experimental condition name
        cfg: Configuration object

    Returns:
        List of tool definitions in OpenAI function calling format
    """
    tool_names = cfg.condition_tools.get(condition, cfg.condition_tools["baseline"])
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]


# =============================================================================
# Agent Context Classes
# =============================================================================

class AgentContext:
    """COM-based context for Excel and PIMS interaction.

    Uses win32com to directly interact with Excel workbooks and PIMS.
    Suitable for single-threaded execution on Windows with Excel installed.
    """

    def __init__(self, xls_path: str, model_dir: str, skip_pims: bool = False):
        """Initialize COM context.

        Args:
            xls_path: Path to Excel workbook
            model_dir: Path to PIMS model directory
            skip_pims: If True, skip PIMS execution (dry-run mode)
        """
        self.xls_path = xls_path
        self.model_dir = model_dir
        self.skip_pims = skip_pims
        self.backup_path = xls_path + ".bak_agent"

        # Create backup
        if os.path.exists(xls_path):
            shutil.copy2(xls_path, self.backup_path)

        # Excel COM handles (lazy initialization)
        self._xl: Any = None
        self._wb: Any = None

        # State tracking
        self.case_entries_written: List[List[str]] = []
        self.case_numbers: List[int] = []
        self.pims_result: Dict[str, Any] = {
            "status": None,
            "objective": None,
            "converged": False,
        }

    def _ensure_excel(self) -> None:
        """Initialize Excel COM if not already done."""
        if self._wb is None:
            import win32com.client

            try:
                self._xl = win32com.client.DispatchEx("Excel.Application")
            except Exception:
                self._xl = win32com.client.Dispatch("Excel.Application")
            self._xl.Visible = False
            self._xl.DisplayAlerts = False
            self._wb = self._xl.Workbooks.Open(self.xls_path)

    def close(self, restore: bool = True) -> None:
        """Close Excel handles and optionally restore backup.

        Args:
            restore: If True, restore the original Excel file from backup
        """
        if self._wb:
            try:
                self._wb.Close(SaveChanges=False)
            except Exception:
                pass
        if self._xl:
            try:
                self._xl.Quit()
            except Exception:
                pass
        self._xl = None
        self._wb = None
        gc.collect()

        if restore and os.path.exists(self.backup_path):
            try:
                shutil.copy2(self.backup_path, self.xls_path)
                os.remove(self.backup_path)
            except Exception:
                pass


class JsonContext:
    """File-based context using pre-exported JSON files.

    Reads table data from JSON exports and writes via xlrd/xlwt.
    No COM dependency required - works on any platform.
    """

    def __init__(
        self,
        xls_path: str,
        model_dir: str,
        json_dir: Path,
        skip_pims: bool = False,
        condition: str = "baseline",
        skill_dir: Optional[str] = None,
    ):
        """Initialize JSON context.

        Args:
            xls_path: Path to Excel workbook (for xlwt writes)
            model_dir: Path to PIMS model directory
            json_dir: Path to directory containing JSON exports
            skip_pims: If True, skip PIMS execution
            condition: Experimental condition name
            skill_dir: Optional path to skill library
        """
        self.xls_path = xls_path
        self.model_dir = model_dir
        self.json_dir = json_dir
        self.skip_pims = skip_pims
        self.condition = condition
        self.skill_dir = skill_dir
        self.backup_path = xls_path + ".bak_agent" if xls_path else ""

        # Create backup
        if xls_path and os.path.exists(xls_path):
            shutil.copy2(xls_path, self.backup_path)

        # Load sheet index
        self._sheets: List[str] = []
        index_file = json_dir / "sheets_index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                self._sheets = json.load(f).get("sheets", [])

        # Sheet data cache
        self._sheet_cache: Dict[str, Dict] = {}

        # State tracking
        self.case_entries_written: List[List[str]] = []
        self.case_numbers: List[int] = []
        self.pims_result: Dict[str, Any] = {
            "status": None,
            "objective": None,
            "converged": False,
        }

    def _load_sheet(self, sheet_name: str) -> Optional[Dict]:
        """Load sheet data from JSON file.

        Args:
            sheet_name: Name of the sheet to load

        Returns:
            Sheet data dictionary or None if not found
        """
        if sheet_name in self._sheet_cache:
            return self._sheet_cache[sheet_name]

        # Try various filename formats
        safe_name = sheet_name.replace(" ", "_").replace("/", "_")
        candidates = [f"{safe_name}.json", f"{sheet_name}.json"]

        for candidate in candidates:
            fpath = self.json_dir / candidate
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._sheet_cache[sheet_name] = data
                return data

        # Case-insensitive fallback
        for json_file in self.json_dir.glob("*.json"):
            if json_file.stem.lower() == safe_name.lower():
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._sheet_cache[sheet_name] = data
                return data

        return None

    def close(self, restore: bool = True) -> None:
        """Close context and optionally restore backup.

        Args:
            restore: If True, restore the original Excel file from backup
        """
        if restore and self.backup_path and os.path.exists(self.backup_path):
            try:
                shutil.copy2(self.backup_path, self.xls_path)
                os.remove(self.backup_path)
            except Exception:
                pass


# Type alias for context objects
ContextType = Union[AgentContext, JsonContext]


# =============================================================================
# Tool Execution Functions
# =============================================================================

def execute_tool(name: str, args: Dict, ctx: ContextType) -> str:
    """Execute a tool call and return result as JSON string.

    Args:
        name: Tool name
        args: Tool arguments
        ctx: Execution context (AgentContext or JsonContext)

    Returns:
        JSON string with tool result
    """
    try:
        if isinstance(ctx, JsonContext):
            return _execute_tool_json(name, args, ctx)
        else:
            return _execute_tool_com(name, args, ctx)
    except Exception as e:
        logger.exception("Tool execution failed: %s", name)
        return json.dumps({"error": f"{name} failed: {str(e)}"})


def _execute_tool_com(name: str, args: Dict, ctx: AgentContext) -> str:
    """Execute tool using COM (Excel + PIMS)."""
    if name == "list_sheets":
        return _tool_list_sheets_com(ctx)
    elif name == "read_sheet":
        return _tool_read_sheet_com(ctx, args.get("sheet_name", ""))
    elif name == "read_cell":
        return _tool_read_cell_com(
            ctx,
            args.get("sheet_name", ""),
            args.get("row_tag", ""),
            args.get("col_header", ""),
        )
    elif name == "write_case":
        return _tool_write_case_com(
            ctx,
            args.get("case_number", 0),
            args.get("description", ""),
            args.get("entries", []),
        )
    elif name == "run_pims":
        return _tool_run_pims(ctx, args.get("case_numbers", ""))
    elif name == "read_doc":
        return _tool_read_doc(args.get("table_name", ""))
    elif name == "read_skill":
        return _tool_read_skill(
            args.get("skill_name", ""),
            condition=getattr(ctx, "condition", "skill_base"),
            skill_dir=getattr(ctx, "skill_dir", None),
        )
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


def _execute_tool_json(name: str, args: Dict, ctx: JsonContext) -> str:
    """Execute tool using JSON files + xlwt."""
    import copy

    if name == "list_sheets":
        return json.dumps({"sheets": ctx._sheets, "count": len(ctx._sheets)})

    elif name == "read_sheet":
        sheet_name = args.get("sheet_name", "")
        data = ctx._load_sheet(sheet_name)
        if data is None:
            return json.dumps({"error": f"Sheet '{sheet_name}' not found"})

        # Append agent's written entries when reading Case sheet
        if sheet_name.lower() == "case" and ctx.case_entries_written:
            data = copy.deepcopy(data)
            for entries in ctx.case_entries_written:
                for line in entries:
                    parts = [p.strip() for p in line.split("|")]
                    tag = parts[0] if parts else ""
                    text = parts[1] if len(parts) > 1 else ""
                    vals = {}
                    if len(parts) > 2:
                        for i, v in enumerate(parts[2:]):
                            if v:
                                vals[f"col{i + 3}"] = v
                    data["rows"].append({"tag": tag, "text": text, "values": vals})
                data["rows"].append({"tag": "---", "text": "(agent written)", "values": {}})

        return json.dumps(data, default=str, ensure_ascii=False)[:8000]

    elif name == "read_cell":
        sheet_name = args.get("sheet_name", "")
        row_tag = args.get("row_tag", "")
        col_header = args.get("col_header", "")
        data = ctx._load_sheet(sheet_name)
        if data is None:
            return json.dumps({"error": f"Sheet '{sheet_name}' not found"})

        for row in data.get("rows", []):
            if row.get("tag", "").upper() == row_tag.upper():
                val = row.get("values", {}).get(col_header)
                if val is None:
                    # Case-insensitive column lookup
                    for k, v in row.get("values", {}).items():
                        if k.upper() == col_header.upper():
                            val = v
                            break
                return json.dumps(
                    {"sheet": sheet_name, "row": row_tag, "col": col_header, "value": val},
                    default=str,
                )
        return json.dumps({"error": f"Row '{row_tag}' not found in '{sheet_name}'"})

    elif name == "write_case":
        case_num = args.get("case_number", 0)
        description = args.get("description", "")
        entries = args.get("entries", [])
        ctx.case_entries_written.append(entries)
        ctx.case_numbers.append(case_num)

        if ctx.xls_path and not ctx.skip_pims:
            success = _write_case_xlwt(ctx.xls_path, case_num, description, entries)
            return json.dumps(
                {
                    "success": success,
                    "case_number": case_num,
                    "lines_written": len(entries),
                    "method": "xlrd/xlwt",
                }
            )
        else:
            return json.dumps(
                {
                    "success": True,
                    "case_number": case_num,
                    "lines_written": len(entries),
                    "note": "Recorded for scoring (skip-pims mode).",
                }
            )

    elif name == "run_pims":
        if ctx.model_dir and not ctx.skip_pims:
            return _tool_run_pims(ctx, args.get("case_numbers", ""))
        else:
            # Dry-run mode: validate format and return feedback
            total_entries = sum(len(e) for e in ctx.case_entries_written)
            has_table = False
            has_terminator = False
            for entries in ctx.case_entries_written:
                for line in entries:
                    if isinstance(line, str):
                        stripped = line.strip()
                        if stripped.startswith("TABLE") or stripped.startswith("REPLACE"):
                            has_table = True
                        if stripped == "*":
                            has_terminator = True

            format_valid = has_table and has_terminator and total_entries > 0
            ctx.pims_result = {
                "status": "SKIPPED",
                "objective": None,
                "converged": format_valid,
                "format_valid": format_valid,
                "entries_count": total_entries,
            }
            return json.dumps(
                {
                    "status": "SKIPPED",
                    "converged": format_valid,
                    "format_valid": format_valid,
                    "entries_count": total_entries,
                    "message": (
                        f"PIMS skipped (no COM). Format check: "
                        f"{'PASS' if format_valid else 'FAIL'} "
                        f"({total_entries} lines, "
                        f"TABLE={'Y' if has_table else 'N'}, "
                        f"terminator={'Y' if has_terminator else 'N'})."
                    ),
                }
            )

    elif name == "read_doc":
        return _tool_read_doc(args.get("table_name", ""))
    elif name == "read_skill":
        return _tool_read_skill(
            args.get("skill_name", ""),
            condition=ctx.condition,
            skill_dir=ctx.skill_dir,
        )
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# =============================================================================
# COM-based Tool Implementations
# =============================================================================

def _tool_list_sheets_com(ctx: AgentContext) -> str:
    """List all sheets using Excel COM."""
    ctx._ensure_excel()
    sheets = [s.Name for s in ctx._wb.Sheets]
    return json.dumps({"sheets": sheets, "count": len(sheets)})


def _tool_read_sheet_com(ctx: AgentContext, sheet_name: str) -> str:
    """Read sheet structure using Excel COM."""
    ctx._ensure_excel()
    try:
        ws = ctx._wb.Sheets(sheet_name)
    except Exception:
        # Case-insensitive lookup
        for s in ctx._wb.Sheets:
            if s.Name.lower() == sheet_name.lower():
                ws = s
                break
        else:
            return json.dumps({"error": f"Sheet '{sheet_name}' not found"})

    # Read headers (row 3)
    headers = []
    for c in range(1, 51):
        v = ws.Cells(3, c).Value
        if v is None or str(v).strip() in ("", "***"):
            if c > 3:
                break
            continue
        headers.append(str(v).strip())

    # Read data rows (up to 30)
    rows = []
    for r in range(4, 34):
        tag = ws.Cells(r, 1).Value
        if tag is None or str(tag).strip() in ("", "*", "***"):
            if r > 10:
                break
            continue
        tag = str(tag).strip()
        text = ws.Cells(r, 2).Value
        text = str(text).strip() if text else ""

        values = {}
        for i, h in enumerate(headers[2:], start=3):
            v = ws.Cells(r, i).Value
            if v is not None:
                values[h] = v

        rows.append({"tag": tag, "text": text, "values": values})

    return json.dumps(
        {"sheet": sheet_name, "headers": headers, "rows": rows},
        default=str,
        ensure_ascii=False,
    )


def _tool_read_cell_com(ctx: AgentContext, sheet: str, row_tag: str, col: str) -> str:
    """Read specific cell using Excel COM."""
    ctx._ensure_excel()
    try:
        ws = ctx._wb.Sheets(sheet)
    except Exception:
        for s in ctx._wb.Sheets:
            if s.Name.lower() == sheet.lower():
                ws = s
                break
        else:
            return json.dumps({"error": f"Sheet '{sheet}' not found"})

    # Find row by tag (column A)
    row_num = 0
    for r in range(1, 501):
        v = ws.Cells(r, 1).Value
        if v is not None and str(v).strip().upper() == row_tag.strip().upper():
            row_num = r
            break
    if row_num == 0:
        return json.dumps({"error": f"Row '{row_tag}' not found in '{sheet}'"})

    # Find column by header (search common header rows)
    col_num = 0
    for hr in (3, 5, 2, 1, 6, 8):
        for c in range(1, 51):
            v = ws.Cells(hr, c).Value
            if v is not None and str(v).strip().upper() == col.strip().upper():
                col_num = c
                break
        if col_num:
            break
    if col_num == 0:
        return json.dumps({"error": f"Column '{col}' not found in '{sheet}'"})

    value = ws.Cells(row_num, col_num).Value
    return json.dumps(
        {"sheet": sheet, "row": row_tag, "col": col, "value": value},
        default=str,
    )


def _tool_write_case_com(
    ctx: AgentContext, case_num: int, description: str, entries: List[str]
) -> str:
    """Write CASE entries using Excel COM."""
    ctx._ensure_excel()
    cs = ctx._wb.Sheets("Case")
    insert_row = cs.UsedRange.Rows.Count + 2

    # Write CASE header
    cs.Cells(insert_row, 1).Value = f"CASE {case_num}"
    cs.Cells(insert_row, 2).Value = description
    insert_row += 1

    # Write entries
    for line in entries:
        if not line.strip():
            insert_row += 1
            continue
        parts = [p.strip() for p in line.split("|")]

        if parts[0].startswith("CASE"):
            continue  # Already written above
        elif parts[0].startswith("MODIFIES"):
            cs.Cells(insert_row, 1).Value = parts[0]
        elif parts[0] in ("TABLE", "REPLACE"):
            cs.Cells(insert_row, 1).Value = parts[0]
            if len(parts) > 1 and parts[1]:
                cs.Cells(insert_row, 2).Value = parts[1]
        elif parts[0] == "*":
            cs.Cells(insert_row, 1).Value = "*"
        elif not parts[0]:
            # Column headers
            for col_idx, val in enumerate(parts[1:], start=2):
                if val:
                    cs.Cells(insert_row, col_idx).Value = val
        else:
            # Data row
            cs.Cells(insert_row, 1).Value = parts[0]
            for col_idx, val in enumerate(parts[1:], start=2):
                if val:
                    try:
                        if "." in val:
                            cs.Cells(insert_row, col_idx).Value = float(val)
                        else:
                            cs.Cells(insert_row, col_idx).Value = int(val)
                    except ValueError:
                        cs.Cells(insert_row, col_idx).Value = val
        insert_row += 1

    ctx._wb.Save()
    ctx.case_entries_written.append(entries)
    ctx.case_numbers.append(case_num)

    return json.dumps({"success": True, "case_number": case_num, "lines_written": len(entries)})


def _tool_run_pims(ctx: ContextType, case_numbers: str, cfg: Optional[Config] = None) -> str:
    """Run PIMS with specified CASE numbers.

    Args:
        ctx: Execution context
        case_numbers: Comma-separated case numbers
        cfg: Configuration (uses global config if None)

    Returns:
        JSON string with execution result
    """
    if ctx.skip_pims:
        return json.dumps(
            {
                "status": "SKIPPED",
                "objective": None,
                "message": "PIMS execution skipped (--skip-pims mode)",
            }
        )

    if cfg is None:
        cfg = get_config()

    # Determine base objective for delta calculation
    model_key = "WS"  # Default
    if "Gulf" in ctx.model_dir or "GC" in ctx.model_dir:
        model_key = "GC"
    base_objective = cfg.model_paths.get(model_key, {}).get("base_objective", 0)

    try:
        import subprocess

        # Kill any lingering processes
        for proc in ["PIMSWIN.EXE", "EXCEL.EXE"]:
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, timeout=5)
        time.sleep(3)

        from pims_client import AspenPIMS

        pims = AspenPIMS(suppress_ui=True)
        pims.open_model(ctx.model_dir)
        pims.set_display_message_box(False)
        pims.set_suppress_user_interface(True)

        # Re-point tables to Excel file
        xls = os.path.join(ctx.model_dir, "sample.xls")
        all_tables = [
            "BUY", "SELL", "CAPS", "CASE",
            "BLNMIX", "BLNSPEC", "BLNTARG", "BLNREST",
            "PROCLIM", "BOUNDS",
            "CRDCUTS", "CRDQUAL",
            "SUBMODS",
            "SLPR", "SCCU", "SDLC", "SDHT", "SHCD", "CHYD",
            "SIS4", "SSFA", "SGTU", "SVAC",
            "GROUPS", "ECON", "EQUIP",
        ]

        for tbl in all_tables:
            try:
                sheet = tbl
                if tbl == "CASE":
                    sheet = "Case"
                elif tbl in ("BUY", "SELL", "CAPS"):
                    sheet = tbl.capitalize()
                pims.set_table_file(tbl, 0, xls, sheet)
            except Exception:
                pass

        pims.set_cases(case_numbers)
        pims.run_model(False)

        # Extract results
        last_case = int(case_numbers.split(",")[-1].strip())
        pims.set_case_number(last_case)
        obj = float(pims.get_objective_value())
        status = pims.get_solution_status()
        converged = "CONVERGED" in status.upper() or "OPTIMAL" in status.upper()

        ctx.pims_result = {"status": status, "objective": obj, "converged": converged}

        pims.close_model()
        pims.close_pims()
        del pims
        gc.collect()

        return json.dumps(
            {
                "status": status,
                "objective": obj,
                "converged": converged,
                "delta": obj - base_objective,
            }
        )
    except Exception as e:
        logger.exception("PIMS execution failed")
        ctx.pims_result = {
            "status": None,
            "objective": None,
            "converged": False,
            "error": str(e),
        }
        try:
            pims.close_model()
            pims.close_pims()
            del pims
        except Exception:
            pass
        gc.collect()
        return json.dumps({"error": str(e), "status": "FAILED"})


# =============================================================================
# xlwt-based CASE Writing (no COM)
# =============================================================================

def _write_case_xlwt(
    xls_path: str, case_num: int, description: str, entries: List[str]
) -> bool:
    """Write CASE entries using xlrd/xlwt (no Excel COM required).

    Args:
        xls_path: Path to Excel workbook
        case_num: CASE number
        description: Case description
        entries: List of CASE entry lines

    Returns:
        True if successful, False otherwise
    """
    import xlrd
    from xlutils.copy import copy as xlcopy

    try:
        rb = xlrd.open_workbook(xls_path, formatting_info=True)
        wb = xlcopy(rb)

        # Find Case sheet
        case_idx = None
        for i, name in enumerate(rb.sheet_names()):
            if name.lower() == "case":
                case_idx = i
                break
        if case_idx is None:
            return False

        rs = rb.sheet_by_index(case_idx)
        ws = wb.get_sheet(case_idx)
        insert_row = rs.nrows

        # Write CASE header
        ws.write(insert_row, 0, f"CASE {case_num}")
        ws.write(insert_row, 1, description)
        insert_row += 1

        # Write entries
        for line in entries:
            if not line.strip():
                insert_row += 1
                continue
            parts = [p.strip() for p in line.split("|")]

            if parts[0].startswith("CASE"):
                continue
            elif parts[0].startswith("MODIFIES"):
                ws.write(insert_row, 0, parts[0])
            elif parts[0] in ("TABLE", "REPLACE"):
                ws.write(insert_row, 0, parts[0])
                if len(parts) > 1 and parts[1]:
                    ws.write(insert_row, 1, parts[1])
            elif parts[0] == "*":
                ws.write(insert_row, 0, "*")
            elif not parts[0]:
                # Column headers
                for col_idx, val in enumerate(parts[1:], start=1):
                    if val:
                        ws.write(insert_row, col_idx, val)
            else:
                # Data row
                ws.write(insert_row, 0, parts[0])
                for col_idx, val in enumerate(parts[1:], start=1):
                    if val:
                        try:
                            if "." in val:
                                ws.write(insert_row, col_idx, float(val))
                            else:
                                ws.write(insert_row, col_idx, int(val))
                        except ValueError:
                            ws.write(insert_row, col_idx, val)
            insert_row += 1

        wb.save(xls_path)
        return True

    except Exception as e:
        logger.error("xlwt write failed: %s", e)
        return False


# =============================================================================
# Documentation and Skill Reading
# =============================================================================

def _tool_read_doc(table_name: str, cfg: Optional[Config] = None) -> str:
    """Read PIMS documentation for a table.

    Args:
        table_name: Table name to look up
        cfg: Configuration (uses global config if None)

    Returns:
        JSON string with documentation content
    """
    if cfg is None:
        cfg = get_config()

    kb_tables = cfg.knowledge_base_dir / "02-tables"
    docs = []

    if kb_tables.exists():
        for md_file in kb_tables.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            if table_name.upper() in content.upper()[:500]:
                docs.append(content[:3000])

    if not docs:
        kb_basics = cfg.knowledge_base_dir / "01-basics"
        if kb_basics.exists():
            for md_file in kb_basics.rglob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                if table_name.upper() in content.upper()[:200]:
                    docs.append(content[:2000])

    if docs:
        return json.dumps(
            {"table": table_name, "documentation": "\n---\n".join(docs)[:5000]}
        )
    return json.dumps({"table": table_name, "documentation": "No documentation found."})


def _tool_read_skill(
    skill_name: str,
    condition: str = "skill_base",
    skill_dir: Optional[str] = None,
    cfg: Optional[Config] = None,
) -> str:
    """Read compiled skill document.

    Skill routing by condition:
      - skill_refined: refined skills (SkillRefine method)
      - skill_base: unrefined skills or skill_dir if provided
      - ablation_no_signal1: refined with Signal 2 only
      - ablation_no_signal2: refined with Signal 1 only
      - trace2skill: Trace2Skill baseline
      - skillopt: SkillOpt baseline

    Args:
        skill_name: Skill or table name
        condition: Experimental condition
        skill_dir: Optional override path to skill library
        cfg: Configuration (uses global config if None)

    Returns:
        Skill content as string or JSON
    """
    if cfg is None:
        cfg = get_config()

    # Determine skill directory based on condition
    if skill_dir and condition != "skill_base":
        distilled_dir = Path(skill_dir)
    elif condition == "skill_refined":
        distilled_dir = cfg.get_skill_library_path("skill_refined")
    elif condition == "skill_base":
        distilled_dir = Path(skill_dir) if skill_dir else cfg.get_skill_library_path("skill_base")
    else:
        distilled_dir = cfg.get_skill_library_path(condition)

    if distilled_dir and distilled_dir.exists():
        # Handle path-style skill names
        if "/" in skill_name:
            direct = distilled_dir / f"{skill_name}.md"
            if direct.exists():
                return direct.read_text(encoding="utf-8")[:6000]

        # Search in subdirectories
        for subdir in ["procedures", "experience", "table_refs", "submodel"]:
            candidate = distilled_dir / subdir / f"{skill_name}.md"
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")[:6000]
            candidate = distilled_dir / subdir / f"{skill_name.upper()}.md"
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")[:6000]

        # Direct match
        candidate = distilled_dir / f"{skill_name}.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")[:6000]

        # Fuzzy match
        name_lower = skill_name.lower()
        matches = sorted(distilled_dir.glob(f"*{name_lower}*.md"))
        if matches:
            combined = []
            for m in matches[:5]:
                combined.append(f"--- {m.stem} ---\n{m.read_text(encoding='utf-8')[:2000]}")
            return "\n\n".join(combined)[:6000]

    # Fallback to references directory
    refs_dir = cfg.skill_libraries_dir / "references"
    if refs_dir.exists():
        ref_md = refs_dir / f"table_{skill_name.upper()}.md"
        if ref_md.exists():
            return ref_md.read_text(encoding="utf-8")[:6000]

        ref_lower = refs_dir / f"{skill_name.lower()}.md"
        if ref_lower.exists():
            return ref_lower.read_text(encoding="utf-8")[:6000]

        # Special cases
        if skill_name.lower() in ("case", "case_table", "format", "write_operations"):
            guide = refs_dir / "case_table_guide.md"
            if guide.exists():
                return guide.read_text(encoding="utf-8")[:6000]

        if skill_name.lower() in ("table_catalog", "catalog", "tables"):
            catalog = refs_dir / "complete_table_catalog.md"
            if catalog.exists():
                return catalog.read_text(encoding="utf-8")[:6000]

        # JSON fallback
        compiled = refs_dir / f"compiled_{skill_name.upper()}.json"
        if compiled.exists():
            return compiled.read_text(encoding="utf-8")[:5000]

    return json.dumps({"skill": skill_name, "content": "Skill not found."})


# =============================================================================
# System Prompt Builder
# =============================================================================

def build_system_prompt(
    condition: str,
    skill_dir: Optional[str] = None,
    cfg: Optional[Config] = None,
) -> str:
    """Build system prompt for the agent based on experimental condition.

    Args:
        condition: Experimental condition name
        skill_dir: Optional path to skill library
        cfg: Configuration (uses global config if None)

    Returns:
        System prompt string
    """
    if cfg is None:
        cfg = get_config()

    base = """You are an autonomous PIMS operation agent. PIMS is an LP-based refinery planning system stored as an Excel workbook with interconnected tables.

TASK: Given a business scenario, you MUST:
1. Call list_sheets() to discover tables (1 call)
2. Call read_sheet() on RELEVANT tables only to understand structure
3. IMMEDIATELY call write_case() to make the modifications — YOU MUST DO THIS
4. Call run_pims() to verify — YOU MUST DO THIS
5. Then give your final answer

CRITICAL RULES:
- After reading relevant sheets, you MUST call write_case() immediately
- YOU MUST call write_case() and run_pims() before finishing
- Do NOT just describe what should be done — actually DO it using the tools

CASE table format (for write_case entries parameter):
  "TABLE | TABLE_NAME"          — which table to modify
  " | TEXT | COL1 | COL2 |"    — column headers
  "ROW_TAG | Description | val1 | val2 |" — data row
  "*"                           — terminator

Example entries for changing JET price to 150:
  ["TABLE | SELL", " | TEXT | PRICE |", "JET | Kero/Jet | 150.0 |", "*"]

WORKFLOW:
1. list_sheets() → see what tables exist
2. read_sheet("SELL") → understand SELL structure (if scenario mentions prices)
3. read_sheet("Buy") → understand BUY structure (if scenario mentions purchases)
4. write_case() → write the modifications based on what you learned
5. run_pims() → verify the changes work
"""

    if condition == "doconly":
        base += "\nYou can call read_doc() to look up PIMS documentation for any table.\n"

    elif condition in (
        "skill_base",
        "skill_refined",
        "ablation_no_signal1",
        "ablation_no_signal2",
        "trace2skill",
        "skillopt",
    ):
        # Determine skill path for injecting SKILL.md content
        if skill_dir:
            skill_path = Path(skill_dir)
        else:
            skill_path = cfg.get_skill_library_path(condition)

        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            distilled_content = skill_md.read_text(encoding="utf-8")
        else:
            distilled_content = ""

        base += f"""

## Key Rules (from skill library)
{distilled_content}

You have up to {cfg.max_agent_steps} steps. Use them wisely: read_skill -> read_sheet -> write_case -> run_pims.
"""

    return base


# =============================================================================
# Message Serialization and Compression
# =============================================================================

def _serialize_messages(messages: List) -> List[Dict]:
    """Serialize OpenAI message objects to JSON-safe dicts for logging.

    Args:
        messages: List of message objects or dicts

    Returns:
        List of JSON-serializable dicts
    """
    serialized = []
    for msg in messages:
        if isinstance(msg, dict):
            serialized.append(msg)
        else:
            entry = {"role": getattr(msg, "role", "unknown")}
            if hasattr(msg, "content") and msg.content:
                entry["content"] = msg.content[:5000]
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in msg.tool_calls
                ]
            if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            serialized.append(entry)
    return serialized


def _estimate_tokens(messages: List) -> int:
    """Estimate token count from messages (rough approximation).

    Args:
        messages: List of message objects or dicts

    Returns:
        Estimated token count
    """
    total = 0
    for m in messages:
        if isinstance(m, dict):
            total += len(m.get("content", "") or "") // 3
            for tc in m.get("tool_calls", []):
                total += len(str(tc)) // 3
        else:
            total += len(str(getattr(m, "content", "") or "")) // 3
    return total


def _compress_messages(
    messages: List,
    compress_threshold: int,
    keep_recent: int = 6,
) -> List:
    """Compress old tool results to free context space.

    Args:
        messages: List of messages
        compress_threshold: Token threshold to trigger compression
        keep_recent: Number of recent messages to keep intact

    Returns:
        Compressed message list
    """
    est = _estimate_tokens(messages)
    if est < compress_threshold:
        return messages

    logger.info("Context ~%d tokens > threshold %d, compressing...", est, compress_threshold)
    compressed = []
    cutoff = max(len(messages) - keep_recent, 0)
    tool_results_compressed = 0

    for i, m in enumerate(messages):
        if i >= cutoff:
            compressed.append(m)
            continue

        # Compress large tool results
        if isinstance(m, dict) and m.get("role") == "tool":
            content = m.get("content", "")
            if len(content) > 300:
                summary = content[:200] + "...[compressed]"
                compressed.append({**m, "content": summary})
                tool_results_compressed += 1
                continue

        # Compress large assistant messages without tool calls
        if isinstance(m, dict) and m.get("role") == "assistant":
            content = m.get("content", "") or ""
            if len(content) > 500 and not m.get("tool_calls"):
                compressed.append({**m, "content": content[:300] + "...[compressed]"})
                continue

        compressed.append(m)

    new_est = _estimate_tokens(compressed)
    logger.info(
        "%d tool results compressed, ~%d -> ~%d tokens",
        tool_results_compressed,
        est,
        new_est,
    )
    return compressed


# =============================================================================
# Agent Loop
# =============================================================================

def run_agent(
    task: Dict,
    condition: str,
    model: Optional[str] = None,
    skip_pims: bool = False,
    system_prompt: Optional[str] = None,
    skill_dir: Optional[str] = None,
) -> Dict:
    """Run the tool-calling agent on a single task.

    Args:
        task: Task dictionary with 'id', 'scenario', 'model', etc.
        condition: Experimental condition (e.g., 'baseline', 'skill_refined')
        model: Model key (e.g., 'deepseek-pro')
        skip_pims: If True, skip PIMS execution
        system_prompt: Optional custom system prompt (overrides condition-based prompt)
        skill_dir: Optional path to skill library

    Returns:
        Result dictionary with tool_calls, case_entries, pims_result, scores, errors, steps
    """
    import openai

    cfg = get_config()
    task_id = task["id"]
    scenario = task["scenario"]
    model_id = cfg.get_model_id(model or cfg.default_model)

    # Build result structure
    result: Dict[str, Any] = {
        "task_id": task_id,
        "level": task.get("level"),
        "condition": condition,
        "model": model_id,
        "scenario": scenario,
        "tool_calls": [],
        "case_entries": [],
        "pims_result": {"status": None, "objective": None, "converged": False},
        "scores": {},
        "errors": [],
        "steps": 0,
    }

    logger.info(
        "\n%s\n  [%s] %s: %s...\n  Model: %s\n%s",
        "=" * 70,
        condition,
        task_id,
        scenario[:60],
        model_id,
        "=" * 70,
    )

    # Initialize OpenAI client
    client = openai.OpenAI(
        base_url=cfg.llm_api_base,
        api_key=cfg.llm_api_key,
        timeout=120.0,
    )

    # API call configuration
    api_kwargs = {
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
        "tool_choice": "auto",
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }

    def call_llm(messages: List, tools: List, **overrides) -> Any:
        """Call LLM with common settings."""
        kw = {**api_kwargs, **overrides}
        return client.chat.completions.create(
            model=model_id, messages=messages, tools=tools, **kw
        )

    # Context compression settings
    context_limit = 32768 if "qwen" in model_id.lower() else 131072
    max_output = api_kwargs.get("max_tokens", 8192)
    compress_threshold = int((context_limit - max_output) * 0.75)

    # Get tools for condition
    tools = get_tools_for_condition(condition, cfg)

    # Build initial messages
    prompt = system_prompt if system_prompt else build_system_prompt(condition, skill_dir, cfg)
    messages: List = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": scenario},
    ]

    # Select model-specific paths
    model_key = task.get("model", "WS")
    model_cfg = cfg.model_paths.get(model_key, cfg.model_paths["WS"])

    # Create context
    json_dir = cfg.excel_json_ws if model_key == "WS" else cfg.excel_json_gc
    ctx = JsonContext(
        xls_path=model_cfg["xls_path"],
        model_dir=model_cfg["model_dir"],
        json_dir=json_dir,
        skip_pims=skip_pims,
        condition=condition,
        skill_dir=skill_dir,
    )

    # Agent loop state
    max_steps = cfg.max_agent_steps
    anti_paralysis_threshold = 12  # Force write_case after N steps
    read_sheet_paralysis_threshold = 20  # Fire anti-paralysis after N read_sheet calls
    loop_detection_window = 5  # Detect loops over N consecutive identical calls
    max_empty_responses = 8  # Break after N empty responses

    try:
        recent_tools: List[str] = []
        anti_paralysis_fired = False
        consecutive_loop_detects = 0
        total_empty = 0

        for step in range(max_steps):
            result["steps"] = step + 1

            # Anti-paralysis: force write_case if not called after threshold steps
            if step >= anti_paralysis_threshold and not ctx.case_entries_written:
                logger.warning(
                    "Step %d: Forcing write_case after %d steps", step + 1, step
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"You have completed {step} steps without calling write_case(). "
                            "You MUST call write_case() NOW with whatever CASE entries you can "
                            "construct from what you have read so far. This is MANDATORY. "
                            "Call write_case() immediately, then call run_pims()."
                        ),
                    }
                )
                messages = _compress_messages(messages, compress_threshold)

                # Force write_case call
                force_response = call_llm(
                    messages=messages,
                    tools=tools,
                    tool_choice={"type": "function", "function": {"name": "write_case"}},
                )
                force_msg = force_response.choices[0].message
                if force_msg.tool_calls:
                    for tc in force_msg.tool_calls:
                        fn_name = tc.function.name
                        fn_args = json.loads(tc.function.arguments)
                        logger.info("Force: %s(%s)", fn_name, json.dumps(fn_args)[:200])
                        tool_result = execute_tool(fn_name, fn_args, ctx)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_result,
                            }
                        )

                # Force run_pims call
                logger.info("Step %d: Forcing run_pims after write_case", step + 1)
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You have written CASE entries. Now you MUST call run_pims() "
                            "to verify the modifications. Call run_pims() immediately."
                        ),
                    }
                )
                force_response2 = call_llm(
                    messages=messages,
                    tools=tools,
                    tool_choice={"type": "function", "function": {"name": "run_pims"}},
                )
                force_msg2 = force_response2.choices[0].message
                if force_msg2.tool_calls:
                    for tc in force_msg2.tool_calls:
                        fn_name = tc.function.name
                        fn_args = json.loads(tc.function.arguments)
                        logger.info("Force: %s(%s)", fn_name, json.dumps(fn_args)[:200])
                        tool_result = execute_tool(fn_name, fn_args, ctx)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_result,
                            }
                        )
                break

            # Loop detection: break if same tool+args called repeatedly
            if len(recent_tools) >= loop_detection_window:
                last_n = recent_tools[-loop_detection_window:]
                if all(t == last_n[0] for t in last_n):
                    consecutive_loop_detects += 1
                    tool_name = last_n[0].split(":")[0] if ":" in last_n[0] else last_n[0]
                    logger.warning(
                        "Step %d: Loop detected (%s x%d), forcing finish (#%d)",
                        step + 1,
                        tool_name,
                        loop_detection_window,
                        consecutive_loop_detects,
                    )
                    if consecutive_loop_detects >= 2:
                        if not ctx.case_entries_written:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": (
                                        "STOP reading sheets. You MUST call write_case() NOW "
                                        "with whatever CASE entries you can construct. "
                                        "This is your LAST chance. Call write_case() immediately."
                                    ),
                                }
                            )
                            force_response = call_llm(messages=messages, tools=tools)
                            force_msg = force_response.choices[0].message
                            if force_msg.tool_calls:
                                for tc in force_msg.tool_calls:
                                    fn_name = tc.function.name
                                    fn_args = json.loads(tc.function.arguments)
                                    logger.info("Force: %s(...)", fn_name)
                                    execute_tool(fn_name, fn_args, ctx)
                                    if fn_name == "write_case":
                                        break
                        break

            # Call LLM
            try:
                messages = _compress_messages(messages, compress_threshold)
                response = None
                for retry in range(3):
                    try:
                        response = call_llm(messages=messages, tools=tools)
                        break
                    except Exception as retry_err:
                        logger.warning("LLM API retry %d/3: %s", retry + 1, retry_err)
                        if retry == 2:
                            raise
                        time.sleep(5 * (retry + 1))
            except Exception as api_err:
                logger.error("LLM API error (all retries failed): %s", api_err)
                result["errors"].append(f"LLM API error at step {step}: {api_err}")
                break

            # Track token usage
            if response.usage:
                result["tokens_prompt"] = (
                    result.get("tokens_prompt", 0) + response.usage.prompt_tokens
                )
                result["tokens_completion"] = (
                    result.get("tokens_completion", 0) + response.usage.completion_tokens
                )
                result["tokens_total"] = (
                    result.get("tokens_total", 0) + response.usage.total_tokens
                )

            msg = response.choices[0].message
            messages.append(msg)

            # Handle tool calls
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)

                    logger.info(
                        "Step %d: %s(%s)",
                        step + 1,
                        fn_name,
                        json.dumps(fn_args, ensure_ascii=False)[:200],
                    )
                    result["tool_calls"].append(
                        {"step": step + 1, "name": fn_name, "args": fn_args}
                    )

                    # Track for loop detection
                    tool_key = f"{fn_name}:{json.dumps(fn_args, sort_keys=True)}"
                    recent_tools.append(tool_key)
                    if len(recent_tools) > 20:
                        recent_tools = recent_tools[-20:]

                    # Execute tool
                    tool_result = execute_tool(fn_name, fn_args, ctx)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_result,
                        }
                    )

                # Anti-paralysis check for excessive read_sheet calls
                total_read_sheet = sum(
                    1 for tc in result["tool_calls"] if tc.get("name") == "read_sheet"
                )
                total_write_case = sum(
                    1 for tc in result["tool_calls"] if tc.get("name") == "write_case"
                )
                if (
                    not anti_paralysis_fired
                    and total_read_sheet >= read_sheet_paralysis_threshold
                    and total_write_case == 0
                ):
                    anti_paralysis_fired = True
                    logger.warning(
                        "Anti-paralysis: %d read_sheet calls without write_case. Forcing write.",
                        total_read_sheet,
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"URGENT: You have read {total_read_sheet} sheets without "
                                "calling write_case(). You MUST call write_case() NOW with "
                                "your best guess based on what you've read. Do NOT read more "
                                "sheets. Write the CASE entries immediately."
                            ),
                        }
                    )

            elif msg.content:
                # Model returned text content (no tool calls)
                if not ctx.case_entries_written:
                    logger.info(
                        "Step %d: Agent provided text but hasn't called write_case(). Continuing.",
                        step + 1,
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Good progress. Now please call write_case() with the CASE "
                                "entries you've prepared, then call run_pims() to verify."
                            ),
                        }
                    )
                    continue
                elif not ctx.case_numbers or not ctx.pims_result.get("status"):
                    if not ctx.skip_pims:
                        logger.info(
                            "Step %d: CASE written but run_pims() not called. Continuing.",
                            step + 1,
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Good, CASE entries are written. Now call run_pims() "
                                    "to verify the changes."
                                ),
                            }
                        )
                        continue
                # Agent completed the workflow
                logger.info("Step %d: Agent finished (complete)", step + 1)
                result["final_response"] = msg.content
                break

            else:
                # Empty response
                total_empty += 1
                logger.warning("Step %d: Empty response (#%d)", step + 1, total_empty)

                if total_empty >= max_empty_responses + 4:
                    logger.error("Too many empty responses, giving up.")
                    break

                if total_empty >= max_empty_responses:
                    if not ctx.case_entries_written:
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "You keep returning empty responses. You MUST call "
                                    "write_case() NOW with whatever CASE entries you can "
                                    "construct. This is your LAST chance."
                                ),
                            }
                        )
                        force_response = call_llm(messages=messages, tools=tools)
                        force_msg = force_response.choices[0].message
                        if force_msg.tool_calls:
                            for tc in force_msg.tool_calls:
                                fn_name = tc.function.name
                                fn_args = json.loads(tc.function.arguments)
                                logger.info("Force: %s(...)", fn_name)
                                execute_tool(fn_name, fn_args, ctx)
                                if fn_name == "write_case":
                                    break
                    break

                if not ctx.case_entries_written and step < max_steps - 1:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You must call write_case() NOW with the CASE entries based "
                                "on what you've read. Do NOT return an empty response. "
                                "Write the CASE entries immediately."
                            ),
                        }
                    )
                    continue
                break

        # Post-loop safety net: force write_case if not called
        if not ctx.case_entries_written:
            logger.warning(
                "Agent finished without calling write_case(). Forcing final attempt."
            )

            # Attempt 1: Force with full context
            for force_attempt in range(3):
                try:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"You have NOT called write_case() yet. This is attempt "
                                f"{force_attempt + 1}/3. You MUST call write_case() NOW. "
                                "Do NOT return text. Do NOT read more sheets. "
                                "JUST call write_case() immediately with whatever data you have."
                            ),
                        }
                    )
                    messages = _compress_messages(messages, compress_threshold)
                    force_response = call_llm(
                        messages=messages,
                        tools=tools,
                        tool_choice={"type": "function", "function": {"name": "write_case"}},
                    )
                    force_msg = force_response.choices[0].message
                    if force_msg.tool_calls:
                        for tc in force_msg.tool_calls:
                            fn_name = tc.function.name
                            fn_args = json.loads(tc.function.arguments)
                            logger.info("Final force (attempt %d): %s(...)", force_attempt + 1, fn_name)
                            tool_result = execute_tool(fn_name, fn_args, ctx)
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": tool_result,
                                }
                            )
                            if fn_name == "write_case":
                                break
                    if ctx.case_entries_written:
                        break
                except Exception as force_err:
                    logger.error("Final force attempt %d error: %s", force_attempt + 1, force_err)
                    time.sleep(3)

            # Attempt 2: Aggressive fallback with minimal context
            if not ctx.case_entries_written:
                logger.info("Aggressive fallback: building minimal context...")
                sheets_read = set()
                cells_read = []
                for tc in result.get("tool_calls", []):
                    if tc.get("name") == "read_sheet":
                        sn = tc.get("args", {}).get("sheet_name", "")
                        if sn:
                            sheets_read.add(sn)
                    elif tc.get("name") == "read_cell":
                        cells_read.append(
                            f"{tc.get('args', {}).get('sheet_name', '')}: "
                            f"{tc.get('args', {}).get('row_tag', '')}/"
                            f"{tc.get('args', {}).get('col_header', '')}"
                        )

                sheet_summary = ", ".join(sorted(sheets_read)) if sheets_read else "none"
                cell_summary = "; ".join(cells_read[:10]) if cells_read else "none"

                minimal_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a PIMS agent. You MUST call write_case() with CASE "
                            "entries based on the scenario. No other tools allowed. "
                            "Even a partial answer is better than nothing."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Scenario: {scenario}\n\n"
                            f"Sheets you read: {sheet_summary}\n"
                            f"Cells you read: {cell_summary}\n\n"
                            "You MUST call write_case() NOW with your best guess. "
                            "Format: TABLE | table_name\\n | TEXT | col1 | col2\\n"
                            "row_tag | description | val1 | val2\\n*\n\n"
                            "Call write_case() immediately."
                        ),
                    },
                ]

                for fb_attempt in range(3):
                    try:
                        fallback_response = call_llm(
                            messages=minimal_messages,
                            tools=tools,
                            tool_choice={"type": "function", "function": {"name": "write_case"}},
                        )
                        fallback_msg = fallback_response.choices[0].message
                        if fallback_msg.tool_calls:
                            for tc in fallback_msg.tool_calls:
                                fn_name = tc.function.name
                                fn_args = json.loads(tc.function.arguments)
                                logger.info("Fallback force (attempt %d): %s(...)", fb_attempt + 1, fn_name)
                                if fn_name == "write_case":
                                    execute_tool(fn_name, fn_args, ctx)
                                    break
                        if ctx.case_entries_written:
                            break
                    except Exception as fallback_err:
                        logger.error("Aggressive fallback attempt %d error: %s", fb_attempt + 1, fallback_err)
                        time.sleep(3)

        # Collect results
        result["case_entries"] = ctx.case_entries_written
        result["case_numbers"] = ctx.case_numbers
        result["pims_result"] = ctx.pims_result
        result["conversation"] = _serialize_messages(messages)

        logger.info(
            "Steps: %d | Tool calls: %d",
            result["steps"],
            len(result["tool_calls"]),
        )

    except Exception as e:
        result["errors"].append(f"Agent error: {str(e)}")
        logger.error("Agent error: %s", e)
        traceback.print_exc()

    finally:
        ctx.close(restore=True)

    return result


# =============================================================================
# Experiment Runner
# =============================================================================

def run_experiment(
    condition: str,
    task_ids: Optional[List[str]] = None,
    levels: Optional[List[int]] = None,
    model: Optional[str] = None,
    skip_pims: bool = False,
    n_runs: int = 5,
) -> List[Dict]:
    """Run agent experiment with multiple independent runs per task.

    Paper: "mean and standard deviation computed over five independent
    executions and then averaged across the 100 held-out tasks."

    Each task is executed n_runs times independently. Results are saved
    after each run for checkpointing. The output includes per-task
    mean/std scores across runs.

    Args:
        condition: Experimental condition name
        task_ids: Optional list of specific task IDs to run
        levels: Optional list of complexity levels to filter
        model: Model key (e.g., 'deepseek-pro')
        skip_pims: If True, skip PIMS execution
        n_runs: Number of independent runs per task (default: 5, per paper)

    Returns:
        List of result dictionaries with per-run and aggregated scores
    """
    from skillrefine.scoring import load_benchmark_tasks, score_task, extract_oracle_components
    import math

    cfg = get_config()

    # Load tasks
    tasks = load_benchmark_tasks(
        cfg.bench_eval_path,
        task_ids=task_ids,
        levels=levels,
    )
    if not tasks:
        logger.warning("No tasks found.")
        return []

    model_name = model or cfg.default_model
    cfg.results_dir.mkdir(parents=True, exist_ok=True)

    # Fixed output file per condition+model
    output_file = cfg.results_dir / f"agent_{condition}_{model_name}.json"

    # Load existing results for resume
    # Key: (task_id, run_id) -> result dict
    existing: Dict[str, Dict] = {}
    if output_file.exists():
        try:
            with open(output_file, encoding="utf-8") as f:
                prev = json.load(f)
            for r in prev.get("results", []):
                key = f"{r['task_id']}_run{r.get('run_id', 1)}"
                existing[key] = r
            logger.info("Resumed: %d task-runs already done", len(existing))
        except Exception:
            pass

    total_runs = len(tasks) * n_runs
    logger.info(
        "\n%s\n  Agent Runner: %s | Model: %s\n"
        "  Tasks: %d | Runs/task: %d | Total: %d | Done: %d | Remaining: %d\n"
        "  Output: %s\n%s",
        "=" * 70,
        condition,
        model_name,
        len(tasks),
        n_runs,
        total_runs,
        len(existing),
        total_runs - len(existing),
        output_file,
        "=" * 70,
    )

    results = list(existing.values())

    for i, task in enumerate(tasks):
        tid = task["id"]

        for run_id in range(1, n_runs + 1):
            key = f"{tid}_run{run_id}"

            # Skip completed task-runs
            if key in existing:
                continue

            result = run_agent(task, condition, model=model, skip_pims=skip_pims)
            result["run_id"] = run_id
            result["n_runs"] = n_runs
            results.append(result)

            # Save conversation log separately
            conv_dir = cfg.results_dir / "conversations" / f"{condition}_{model_name}"
            conv_dir.mkdir(parents=True, exist_ok=True)
            conv_file = conv_dir / f"{tid}_run{run_id}.json"
            conversation = result.pop("conversation", [])
            with open(conv_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "task_id": tid,
                        "run_id": run_id,
                        "condition": condition,
                        "model": model_name,
                        "scenario": task.get("scenario", ""),
                        "messages": conversation,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            # Save after each task-run (resume-safe)
            _save_experiment_results(results, output_file, condition, model_name,
                                     len(tasks), n_runs)

            done = len(results)
            logger.info("[%d/%d] %s run %d/%d", done, total_runs, tid, run_id, n_runs)

    # Compute per-task aggregated scores (mean ± std across runs)
    _compute_aggregated_scores(results, tasks, n_runs)

    # Print summary
    _print_summary(results, condition, model_name)

    return results


def _save_experiment_results(
    results: List[Dict],
    output_file: Path,
    condition: str,
    model_name: str,
    n_tasks: int,
    n_runs: int,
) -> None:
    """Save experiment results with metadata."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "condition": condition,
                "model": model_name,
                "n_runs": n_runs,
                "tasks_total": n_tasks,
                "total_runs": n_tasks * n_runs,
                "tasks_done": len(results),
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


def _compute_aggregated_scores(
    results: List[Dict],
    tasks: List[Dict],
    n_runs: int,
) -> None:
    """Compute per-task mean and std scores across runs.

    Adds 'aggregated_scores' to each result for the same task,
    containing mean and std of each metric across runs.

    Paper: "For each task, the mean and standard deviation are computed
    over five independent executions."
    """
    import math

    # Group results by task_id
    by_task: Dict[str, List[Dict]] = {}
    for r in results:
        tid = r.get("task_id", "")
        if tid not in by_task:
            by_task[tid] = []
        by_task[tid].append(r)

    metric_keys = [
        "match", "table_f1", "row_recall", "col_recall", "syntax",
        "value_accuracy", "match_recall", "match_precision",
    ]

    for tid, task_results in by_task.items():
        scores_list = [r.get("scores", {}) for r in task_results]
        n = len(scores_list)

        aggregated = {}
        for key in metric_keys:
            vals = [s.get(key, 0.0) for s in scores_list if key in s]
            if not vals:
                continue
            mean = sum(vals) / len(vals)
            if len(vals) > 1:
                variance = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
                std = math.sqrt(variance)
                sem = std / math.sqrt(len(vals))
            else:
                std = 0.0
                sem = 0.0
            aggregated[key] = {
                "mean": round(mean, 4),
                "std": round(std, 4),
                "sem": round(sem, 4),
                "n": len(vals),
            }

        # Attach aggregated scores to each result for this task
        for r in task_results:
            r["aggregated_scores"] = aggregated


def _print_summary(results: List[Dict], condition: str, model: str) -> None:
    """Print summary of experiment results.

    Args:
        results: List of result dictionaries
        condition: Condition name
        model: Model name
    """
    logger.info("\n%s\n  Summary: %s | %s\n%s", "=" * 70, condition, model, "=" * 70)

    # Count by error type
    error_counts: Dict[str, int] = {}
    for r in results:
        et = r.get("scores", {}).get("error_type", "unknown")
        error_counts[et] = error_counts.get(et, 0) + 1

    total = len(results)
    logger.info("Total: %d tasks", total)
    for et, count in sorted(error_counts.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d (%d%%)", et, count, count * 100 // total if total else 0)

    # Average scores
    if results:
        logger.info("Average scores:")
        for metric in ["syntax", "table_f1", "row_recall", "col_recall", "match"]:
            vals = [r.get("scores", {}).get(metric, 0) for r in results]
            avg = sum(vals) / len(vals) if vals else 0
            logger.info("  %s: %.3f", metric, avg)

    logger.info("=" * 70)
