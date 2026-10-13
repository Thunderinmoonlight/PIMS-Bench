"""Tool definitions and execution for the PIMS agent.

Defines all agent tools in OpenAI function-calling format and provides
execution dispatchers for both JSON (no-COM) and COM-based modes.

Tool catalog (matching paper Table 3):
    - ``list_sheets``: Discover available tables in the Excel workbook
    - ``read_sheet``: Read table structure (headers + data rows)
    - ``read_cell``: Read a specific cell by sheet/row/column
    - ``write_case``: Write CASE table entries for PIMS modifications
    - ``run_pims``: Execute PIMS solver and retrieve results
    - ``read_doc``: Read PIMS documentation for a table
    - ``read_skill``: Read compiled skill documents

Usage::

    from skillrefine.tools import CONDITION_TOOLS, execute_tool_json
    tools = CONDITION_TOOLS["skill_refined"]
    result = execute_tool_json("read_sheet", {"sheet_name": "Sell"}, ctx)
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# =========================================================================
# Tool Definitions (OpenAI function calling format)
# =========================================================================

TOOL_LIST_SHEETS: Dict[str, Any] = {
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

TOOL_READ_SHEET: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_sheet",
        "description": (
            "Read a sheet's structure: headers (row 3) and data rows "
            "(col A = row tag, col B = text, rest = values). "
            "Returns up to 30 rows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {
                    "type": "string",
                    "description": "Sheet name (e.g., 'Buy', 'Sell', 'Caps')",
                },
            },
            "required": ["sheet_name"],
        },
    },
}

TOOL_READ_CELL: Dict[str, Any] = {
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

TOOL_WRITE_CASE: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "write_case",
        "description": (
            "Write CASE table entries to the Case sheet. These modifications "
            "will be applied when PIMS runs. Format each entry as a string "
            "line. End with '*'."
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
                        "['TABLE | SELL', ' | TEXT | PRICE |', "
                        "'JET | Kero/Jet | 150.0 |', '*']"
                    ),
                },
            },
            "required": ["case_number", "description", "entries"],
        },
    },
}

TOOL_RUN_PIMS: Dict[str, Any] = {
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
                    "description": (
                        "Case numbers to run, e.g., '001,101' or '001,101,102'"
                    ),
                },
            },
            "required": ["case_numbers"],
        },
    },
}

TOOL_READ_DOC: Dict[str, Any] = {
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

TOOL_READ_SKILL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_skill",
        "description": (
            "Read a compiled skill document containing structured table "
            "schemas, column constraints, and operation rules."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": (
                        "Skill/table name (e.g., 'BUY', 'SELL', 'CAPS', 'BLENDS')"
                    ),
                },
            },
            "required": ["skill_name"],
        },
    },
}


# All tool definitions in a lookup dict
ALL_TOOLS: Dict[str, Dict[str, Any]] = {
    "list_sheets": TOOL_LIST_SHEETS,
    "read_sheet": TOOL_READ_SHEET,
    "read_cell": TOOL_READ_CELL,
    "write_case": TOOL_WRITE_CASE,
    "run_pims": TOOL_RUN_PIMS,
    "read_doc": TOOL_READ_DOC,
    "read_skill": TOOL_READ_SKILL,
}


# =========================================================================
# Tool assignment per condition (matching paper Table 3)
# =========================================================================

CONDITION_TOOLS: Dict[str, List[Dict[str, Any]]] = {
    # --- 6 main conditions ---
    "baseline": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS,
    ],
    "doconly": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC,
    ],
    "skill_base": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC, TOOL_READ_SKILL,
    ],
    "skill_refined": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC, TOOL_READ_SKILL,
    ],
    "trace2skill": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC, TOOL_READ_SKILL,
    ],
    "skillopt": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC, TOOL_READ_SKILL,
    ],
    # --- ablation conditions (same tools as skill_refined, different library) ---
    "ablation_no_signal1": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC, TOOL_READ_SKILL,
    ],
    "ablation_no_signal2": [
        TOOL_LIST_SHEETS, TOOL_READ_SHEET, TOOL_READ_CELL,
        TOOL_WRITE_CASE, TOOL_RUN_PIMS, TOOL_READ_DOC, TOOL_READ_SKILL,
    ],
}


def get_tools_for_condition(condition: str) -> List[Dict[str, Any]]:
    """Get the tool definitions available for a given experimental condition.

    Matches the tool availability described in paper Table 3:

    ================  ====================================================
    Condition         Tools
    ================  ====================================================
    baseline          list_sheets, read_sheet, read_cell, write_case, run_pims
    doconly           + read_doc
    skill_base        + read_doc, read_skill
    skill_refined     + read_doc, read_skill
    trace2skill       + read_doc, read_skill
    skillopt          + read_doc, read_skill
    ================  ====================================================

    Args:
        condition: Condition name (e.g., ``"baseline"``, ``"skill_refined"``).

    Returns:
        List of OpenAI function-calling tool definitions.
    """
    return CONDITION_TOOLS.get(condition, CONDITION_TOOLS["baseline"])


# =========================================================================
# JSON-mode tool execution (reads from pre-exported JSON, no Excel COM)
# =========================================================================

def execute_tool_json(
    name: str,
    args: Dict[str, Any],
    ctx: Any,
) -> str:
    """Execute a tool call in JSON mode (no Excel COM required).

    Reads sheet data from pre-exported JSON files. Write operations
    are recorded in memory and optionally written via xlrd/xlwt when
    PIMS execution is enabled.

    Args:
        name: Tool function name (e.g., ``"read_sheet"``).
        args: Tool arguments dictionary.
        ctx: Execution context (``JsonContext`` instance).

    Returns:
        JSON-encoded result string.
    """
    try:
        if name == "list_sheets":
            return _json_list_sheets(ctx)
        elif name == "read_sheet":
            return _json_read_sheet(ctx, args.get("sheet_name", ""))
        elif name == "read_cell":
            return _json_read_cell(
                ctx,
                args.get("sheet_name", ""),
                args.get("row_tag", ""),
                args.get("col_header", ""),
            )
        elif name == "write_case":
            return _json_write_case(
                ctx,
                args.get("case_number", 0),
                args.get("description", ""),
                args.get("entries", []),
            )
        elif name == "run_pims":
            return _json_run_pims(ctx, args.get("case_numbers", ""))
        elif name == "read_doc":
            return _exec_read_doc(args.get("table_name", ""), ctx)
        elif name == "read_skill":
            return _exec_read_skill(
                args.get("skill_name", ""),
                condition=getattr(ctx, "condition", "skill_base"),
                skill_dir=getattr(ctx, "skill_dir", None),
            )
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": f"{name} failed: {str(e)}"})


def _json_list_sheets(ctx: Any) -> str:
    """List sheets from JSON index."""
    sheets = getattr(ctx, "_sheets", [])
    return json.dumps({"sheets": sheets, "count": len(sheets)})


def _json_read_sheet(ctx: Any, sheet_name: str) -> str:
    """Read sheet data from pre-exported JSON."""
    data = ctx._load_sheet(sheet_name)
    if data is None:
        return json.dumps({"error": f"Sheet '{sheet_name}' not found"})

    # If reading Case sheet, append agent's own written entries
    if sheet_name.lower() == "case" and ctx.case_entries_written:
        data = copy.deepcopy(data)
        for entries in ctx.case_entries_written:
            for line in entries:
                parts = [p.strip() for p in line.split("|")]
                tag = parts[0] if parts else ""
                text = parts[1] if len(parts) > 1 else ""
                vals: Dict[str, Any] = {}
                if len(parts) > 2:
                    for i, v in enumerate(parts[2:]):
                        if v:
                            vals[f"col{i + 3}"] = v
                data["rows"].append({"tag": tag, "text": text, "values": vals})
            data["rows"].append(
                {"tag": "---", "text": "(agent written)", "values": {}}
            )

    return json.dumps(data, default=str, ensure_ascii=False)[:8000]


def _json_read_cell(
    ctx: Any, sheet_name: str, row_tag: str, col_header: str
) -> str:
    """Read a specific cell from JSON data."""
    data = ctx._load_sheet(sheet_name)
    if data is None:
        return json.dumps({"error": f"Sheet '{sheet_name}' not found"})

    for row in data.get("rows", []):
        if row.get("tag", "").upper() == row_tag.upper():
            val = row.get("values", {}).get(col_header)
            if val is None:
                # Case-insensitive column fallback
                for k, v in row.get("values", {}).items():
                    if k.upper() == col_header.upper():
                        val = v
                        break
            return json.dumps(
                {
                    "sheet": sheet_name,
                    "row": row_tag,
                    "col": col_header,
                    "value": val,
                },
                default=str,
            )

    return json.dumps({"error": f"Row '{row_tag}' not found in '{sheet_name}'"})


def _json_write_case(
    ctx: Any,
    case_num: int,
    description: str,
    entries: List[str],
) -> str:
    """Record CASE entries and optionally write to Excel via xlrd/xlwt."""
    ctx.case_entries_written.append(entries)
    ctx.case_numbers.append(case_num)

    xls_path = getattr(ctx, "xls_path", "")
    skip_pims = getattr(ctx, "skip_pims", False)

    if xls_path and not skip_pims:
        from skillrefine.utils import write_case_xlwt

        success = write_case_xlwt(xls_path, case_num, description, entries)
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


def _json_run_pims(ctx: Any, case_numbers: str) -> str:
    """Run PIMS or validate format in skip-pims mode."""
    model_dir = getattr(ctx, "model_dir", "")
    skip_pims = getattr(ctx, "skip_pims", False)

    if model_dir and not skip_pims:
        return _com_run_pims(ctx, case_numbers)
    else:
        # Skip-pims mode: validate format and provide feedback
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


# =========================================================================
# COM-mode tool execution (requires Excel + PIMS COM)
# =========================================================================

def execute_tool_com(
    name: str,
    args: Dict[str, Any],
    ctx: Any,
) -> str:
    """Execute a tool call using Excel COM and/or PIMS COM.

    Args:
        name: Tool function name.
        args: Tool arguments dictionary.
        ctx: Execution context (``AgentContext`` instance with COM handles).

    Returns:
        JSON-encoded result string.
    """
    try:
        if name == "list_sheets":
            return _com_list_sheets(ctx)
        elif name == "read_sheet":
            return _com_read_sheet(ctx, args.get("sheet_name", ""))
        elif name == "read_cell":
            return _com_read_cell(
                ctx,
                args.get("sheet_name", ""),
                args.get("row_tag", ""),
                args.get("col_header", ""),
            )
        elif name == "write_case":
            return _com_write_case(
                ctx,
                args.get("case_number", 0),
                args.get("description", ""),
                args.get("entries", []),
            )
        elif name == "run_pims":
            return _com_run_pims(ctx, args.get("case_numbers", ""))
        elif name == "read_doc":
            return _exec_read_doc(args.get("table_name", ""), ctx)
        elif name == "read_skill":
            return _exec_read_skill(
                args.get("skill_name", ""),
                condition=getattr(ctx, "condition", "skill_base"),
                skill_dir=getattr(ctx, "skill_dir", None),
            )
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": f"{name} failed: {str(e)}"})


def _com_list_sheets(ctx: Any) -> str:
    """List sheets via Excel COM."""
    ctx._ensure_excel()
    sheets = [s.Name for s in ctx._wb.Sheets]
    return json.dumps({"sheets": sheets, "count": len(sheets)})


def _com_read_sheet(ctx: Any, sheet_name: str) -> str:
    """Read sheet structure via Excel COM."""
    ctx._ensure_excel()
    try:
        ws = ctx._wb.Sheets(sheet_name)
    except Exception:
        for s in ctx._wb.Sheets:
            if s.Name.lower() == sheet_name.lower():
                ws = s
                break
        else:
            return json.dumps({"error": f"Sheet '{sheet_name}' not found"})

    # Read headers (row 3)
    headers: List[str] = []
    for c in range(1, 51):
        v = ws.Cells(3, c).Value
        if v is None or str(v).strip() in ("", "***"):
            if c > 3:
                break
            continue
        headers.append(str(v).strip())

    # Read data rows (up to 30)
    rows: List[Dict[str, Any]] = []
    for r in range(4, 34):
        tag = ws.Cells(r, 1).Value
        if tag is None or str(tag).strip() in ("", "*", "***"):
            if r > 10:
                break
            continue
        tag = str(tag).strip()
        text = ws.Cells(r, 2).Value
        text = str(text).strip() if text else ""

        values: Dict[str, Any] = {}
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


def _com_read_cell(ctx: Any, sheet: str, row_tag: str, col: str) -> str:
    """Read a specific cell via Excel COM."""
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

    # Find row
    row_num = 0
    for r in range(1, 501):
        v = ws.Cells(r, 1).Value
        if v is not None and str(v).strip().upper() == row_tag.strip().upper():
            row_num = r
            break
    if row_num == 0:
        return json.dumps({"error": f"Row '{row_tag}' not found in '{sheet}'"})

    # Find column (check rows 3, 5, 2, 1, 6, 8)
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


def _com_write_case(
    ctx: Any,
    case_num: int,
    description: str,
    entries: List[str],
) -> str:
    """Write CASE entries via Excel COM."""
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
            continue  # already written above
        elif parts[0].startswith("MODIFIES"):
            cs.Cells(insert_row, 1).Value = parts[0]
        elif parts[0] in ("TABLE", "REPLACE"):
            cs.Cells(insert_row, 1).Value = parts[0]
            if len(parts) > 1 and parts[1]:
                cs.Cells(insert_row, 2).Value = parts[1]
        elif parts[0] == "*":
            cs.Cells(insert_row, 1).Value = "*"
        elif not parts[0] or parts[0] == "":
            for col_idx, val in enumerate(parts[1:], start=2):
                if val:
                    cs.Cells(insert_row, col_idx).Value = val
        else:
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

    return json.dumps(
        {"success": True, "case_number": case_num, "lines_written": len(entries)}
    )


def _com_run_pims(ctx: Any, case_numbers: str) -> str:
    """Run PIMS via COM automation."""
    skip_pims = getattr(ctx, "skip_pims", False)
    if skip_pims:
        return json.dumps(
            {
                "status": "SKIPPED",
                "objective": None,
                "message": "PIMS execution skipped (--skip-pims mode)",
            }
        )

    import gc
    import os
    import time

    try:
        import subprocess as _sp

        for _proc in ["PIMSWIN.EXE", "EXCEL.EXE"]:
            _sp.run(["taskkill", "/F", "/IM", _proc], capture_output=True, timeout=5)
        time.sleep(3)

        from skillrefine.pims_client import AspenPIMS

        model_dir = ctx.model_dir
        pims = AspenPIMS(suppress_ui=True)
        pims.open_model(model_dir)
        pims.set_display_message_box(False)
        pims.set_suppress_user_interface(True)

        # Re-point tables to the agent's Excel workbook
        xls = getattr(ctx, "xls_path", os.path.join(model_dir, "sample.xls"))

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

        base_obj = getattr(ctx, "base_objective", 0.0)
        return json.dumps(
            {
                "status": status,
                "objective": obj,
                "converged": converged,
                "delta": obj - base_obj,
            }
        )
    except Exception as e:
        ctx.pims_result = {
            "status": None,
            "objective": None,
            "converged": False,
            "error": str(e),
        }
        try:
            pims.close_model()
        except Exception:
            pass
        try:
            pims.close_pims()
        except Exception:
            pass
        try:
            del pims
        except Exception:
            pass
        gc.collect()
        return json.dumps({"error": str(e), "status": "FAILED"})


# =========================================================================
# Documentation and skill reading (shared between JSON and COM modes)
# =========================================================================

def _exec_read_doc(table_name: str, ctx: Any = None) -> str:
    """Read PIMS documentation for a table from the knowledge base.

    Searches the knowledge-base directory for markdown files that
    mention the given table name.

    Args:
        table_name: PIMS table name (e.g., ``"BUY"``).
        ctx: Optional context for knowledge base path resolution.

    Returns:
        JSON string with documentation content.
    """
    from skillrefine.config import get_config

    cfg = get_config()
    kb_dir = cfg.knowledge_base_dir

    docs: List[str] = []

    # Search in 02-tables
    tables_dir = kb_dir / "02-tables"
    if tables_dir.exists():
        for md_file in tables_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            if table_name.upper() in content.upper()[:500]:
                docs.append(content[:3000])

    # Fallback to 01-basics
    if not docs:
        basics_dir = kb_dir / "01-basics"
        if basics_dir.exists():
            for md_file in basics_dir.rglob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                if table_name.upper() in content.upper()[:200]:
                    docs.append(content[:2000])

    if docs:
        return json.dumps(
            {"table": table_name, "documentation": "\n---\n".join(docs)[:5000]}
        )
    return json.dumps({"table": table_name, "documentation": "No documentation found."})


def _exec_read_skill(
    skill_name: str,
    condition: str = "skill_base",
    skill_dir: Optional[str] = None,
) -> str:
    """Read a compiled skill document.

    Routes to the appropriate skill library based on the experimental
    condition:

    =====================  ================================================
    Condition              Skill Library
    =====================  ================================================
    skill_refined          Refined skills (Phase 4, dual-signal)
    skill_base             Base skills (Phase 1-3)
    ablation_no_signal1    Stage 2 only (w/o compliance filter)
    ablation_no_signal2    Stage 1 only (w/o match decomposition)
    trace2skill            Trace2Skill baseline
    skillopt               SkillOpt baseline
    =====================  ================================================

    Args:
        skill_name: Skill or table name to look up.
        condition: Experimental condition name.
        skill_dir: Optional explicit skill directory override.

    Returns:
        Skill content string or JSON error.
    """
    from skillrefine.config import get_config

    cfg = get_config()

    # Resolve skill directory
    if skill_dir:
        distilled_dir = Path(skill_dir)
    else:
        distilled_dir = cfg.get_skill_library_path(condition)

    # Check for nested skill/ subdirectory
    skill_subdir = distilled_dir / "skill"
    if skill_subdir.exists():
        distilled_dir = skill_subdir

    if not distilled_dir.exists():
        return json.dumps({"skill": skill_name, "content": "Skill library not found."})

    # Handle path-style skill names (e.g., "submodel/reformer_type")
    if "/" in skill_name:
        direct = distilled_dir / f"{skill_name}.md"
        if direct.exists():
            return direct.read_text(encoding="utf-8")[:6000]

    # Search subdirectories (table_refs first for common table lookups)
    for subdir in ["table_refs", "procedures", "experience", "equipment_refs"]:
        candidate = distilled_dir / subdir / f"{skill_name}.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")[:6000]
        candidate = distilled_dir / subdir / f"{skill_name.upper()}.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")[:6000]

    # Check root level
    candidate = distilled_dir / f"{skill_name}.md"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")[:6000]

    # Fuzzy fallback: find files whose name contains the skill name
    name_lower = skill_name.lower()
    matches = sorted(distilled_dir.glob(f"*{name_lower}*.md"))
    if matches:
        combined: List[str] = []
        for m in matches[:5]:
            combined.append(f"--- {m.stem} ---\n{m.read_text(encoding='utf-8')[:2000]}")
        return "\n\n".join(combined)[:6000]

    return json.dumps({"skill": skill_name, "content": "Skill not found."})


# =========================================================================
# Unified dispatcher
# =========================================================================

def execute_tool(
    name: str,
    args: Dict[str, Any],
    ctx: Any,
    mode: str = "json",
) -> str:
    """Execute a tool call, dispatching to the appropriate mode.

    Args:
        name: Tool function name.
        args: Tool arguments dictionary.
        ctx: Execution context instance.
        mode: Execution mode -- ``"json"`` for pre-exported data,
            ``"com"`` for live Excel/PIMS COM.

    Returns:
        JSON-encoded result string.
    """
    if mode == "com":
        return execute_tool_com(name, args, ctx)
    return execute_tool_json(name, args, ctx)
