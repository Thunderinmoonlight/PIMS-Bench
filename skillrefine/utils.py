"""Shared utility functions for SkillRefine experiments.

Provides common helpers used across the agent, scoring, and experiment
modules:

- Excel backup and restore
- CASE entry writing via xlrd/xlwt (no Excel COM)
- CASE entry parsing into structured components
- JSON response parsing from LLM output
- Logging setup

Usage::

    from skillrefine.utils import (
        backup_excel, restore_excel,
        write_case_xlwt, parse_case_entries,
        parse_llm_json, setup_logging,
    )
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger("skillrefine")


# =========================================================================
# Excel backup / restore
# =========================================================================

def backup_excel(xls_path: str, suffix: str = ".bak_agent") -> str:
    """Create a backup copy of an Excel workbook.

    The backup is idempotent: if a backup already exists, it is not
    overwritten (preserving the original pristine state).

    Args:
        xls_path: Path to the Excel workbook.
        suffix: Backup file suffix.

    Returns:
        Path to the backup file.
    """
    backup_path = xls_path + suffix
    if os.path.exists(xls_path) and not os.path.exists(backup_path):
        shutil.copy2(xls_path, backup_path)
        logger.debug("Created backup: %s", backup_path)
    return backup_path


def restore_excel(xls_path: str, suffix: str = ".bak_agent") -> bool:
    """Restore an Excel workbook from its backup.

    Args:
        xls_path: Path to the Excel workbook.
        suffix: Backup file suffix.

    Returns:
        True if restoration succeeded, False otherwise.
    """
    backup_path = xls_path + suffix
    if os.path.exists(backup_path):
        try:
            shutil.copy2(backup_path, xls_path)
            os.remove(backup_path)
            logger.debug("Restored from backup: %s", backup_path)
            return True
        except Exception as e:
            logger.warning("Restore failed: %s", e)
            return False
    return False


def force_backup(xls_path: str, suffix: str = ".bak_agent") -> str:
    """Create a backup, overwriting any existing backup.

    Args:
        xls_path: Path to the Excel workbook.
        suffix: Backup file suffix.

    Returns:
        Path to the backup file.
    """
    backup_path = xls_path + suffix
    if os.path.exists(xls_path):
        shutil.copy2(xls_path, backup_path)
        logger.debug("Force backup: %s", backup_path)
    return backup_path


# =========================================================================
# CASE entry writing via xlrd/xlwt (no Excel COM required)
# =========================================================================

def write_case_xlwt(
    xls_path: str,
    case_num: int,
    description: str,
    entries: List[str],
) -> bool:
    """Write CASE entries to an Excel workbook using xlrd/xlwt.

    This method does not require Excel COM automation and is safe to
    use when PIMS is not running.

    Args:
        xls_path: Path to the Excel workbook.
        case_num: CASE number (e.g., 400).
        description: Human-readable case description.
        entries: List of pipe-delimited CASE entry strings.

    Returns:
        True on success, False on failure.
    """
    try:
        import xlrd
        from xlutils.copy import copy as xlcopy
    except ImportError:
        logger.error("xlrd/xlutils not installed; cannot write CASE entries")
        return False

    try:
        rb = xlrd.open_workbook(xls_path, formatting_info=True)
        wb = xlcopy(rb)

        # Find Case sheet index
        case_idx = None
        for i, name in enumerate(rb.sheet_names()):
            if name.lower() == "case":
                case_idx = i
                break
        if case_idx is None:
            logger.error("Case sheet not found in %s", xls_path)
            return False

        rs = rb.sheet_by_index(case_idx)
        ws = wb.get_sheet(case_idx)
        insert_row = rs.nrows  # append after last row

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
                continue  # already written above
            elif parts[0].startswith("MODIFIES"):
                ws.write(insert_row, 0, parts[0])
            elif parts[0] in ("TABLE", "REPLACE"):
                ws.write(insert_row, 0, parts[0])
                if len(parts) > 1 and parts[1]:
                    ws.write(insert_row, 1, parts[1])
            elif parts[0] == "*":
                ws.write(insert_row, 0, "*")
            elif not parts[0] or parts[0] == "":
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
        logger.debug(
            "Wrote CASE %d (%d entries) to %s",
            case_num,
            len(entries),
            xls_path,
        )
        return True

    except Exception as e:
        logger.error("xlwt write failed: %s", e)
        return False


# =========================================================================
# CASE entry parsing
# =========================================================================

def parse_case_entries(entries: List[str]) -> List[Dict[str, Any]]:
    """Parse CASE entry lines into structured table modifications.

    Extracts table names, column headers, and data rows from
    pipe-delimited CASE entry strings.

    Args:
        entries: List of pipe-delimited CASE entry strings.

    Returns:
        List of dictionaries, each representing a table modification::

            {
                "table": "SELL",
                "mode": "TABLE",
                "columns": ["TEXT", "PRICE"],
                "rows": [
                    {"tag": "JET", "values": ["Kero/Jet", "150.0"]}
                ]
            }
    """
    tables: List[Dict[str, Any]] = []
    current_table: Optional[Dict[str, Any]] = None

    for line in entries:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]

        # Table declaration
        if parts[0] in ("TABLE", "REPLACE"):
            current_table = {
                "table": parts[1].strip().upper() if len(parts) > 1 else "",
                "mode": parts[0],
                "columns": [],
                "rows": [],
            }
            tables.append(current_table)
            continue

        # Skip CASE, MODIFIES, and terminators
        if parts[0].startswith("CASE") or parts[0].startswith("MODIFIES"):
            continue
        if parts[0] == "*":
            current_table = None
            continue

        if current_table is None:
            continue

        # Header row (first field is empty)
        if not parts[0]:
            current_table["columns"] = [p.upper() for p in parts[1:] if p]
            continue

        # Data row
        if parts[0]:
            row_tag = parts[0].strip()
            values = [p.strip() for p in parts[1:]]
            current_table["rows"].append({"tag": row_tag, "values": values})

    return tables


def extract_tables_from_entries(entries: List[str]) -> List[str]:
    """Extract table names referenced in CASE entries.

    Args:
        entries: List of pipe-delimited CASE entry strings.

    Returns:
        List of unique table names (uppercased).
    """
    tables: List[str] = []
    for line in entries:
        if not isinstance(line, str):
            continue
        parts = [p.strip() for p in line.split("|")]
        if parts[0] in ("TABLE", "REPLACE") and len(parts) > 1:
            table_name = parts[1].strip().upper()
            if table_name and table_name not in tables:
                tables.append(table_name)
    return tables


def flatten_case_entries(entries: Any) -> List[str]:
    """Flatten nested case entries into a flat list of strings.

    Handles cases where entries may be nested lists (from multiple
    write_case calls) or plain strings.

    Args:
        entries: Case entries (may be nested lists or strings).

    Returns:
        Flat list of string entries.
    """
    flat: List[str] = []
    if isinstance(entries, list):
        for block in entries:
            if isinstance(block, list):
                flat.extend(block)
            elif isinstance(block, str):
                flat.append(block)
    elif isinstance(entries, str):
        flat.append(entries)
    return flat


# =========================================================================
# JSON response parsing from LLM output
# =========================================================================

def parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from an LLM response.

    Handles common LLM output patterns:
        - Raw JSON
        - JSON wrapped in markdown code blocks
        - JSON embedded in prose text

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed dictionary, or None if no valid JSON found.
    """
    if not text:
        return None

    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try markdown code block extraction
    patterns = [
        r"```json\s*\n?(.*?)\n?\s*```",
        r"```\s*\n?(.*?)\n?\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except (json.JSONDecodeError, ValueError):
                continue

    # Try finding JSON object boundaries with brace matching
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape_next = False
        end = start

        for i in range(start, len(text)):
            ch = text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if depth == 0 and end > start:
            try:
                obj = json.loads(text[start:end])
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                continue

    return None


def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Alias for ``parse_llm_json`` for backward compatibility.

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed dictionary, or None if no valid JSON found.
    """
    return parse_llm_json(text)


def extract_tool_calls(response: Any) -> List[Dict[str, Any]]:
    """Extract tool calls from an OpenAI API response.

    Args:
        response: OpenAI ChatCompletion response object or dictionary.

    Returns:
        List of tool call dictionaries with ``"id"``, ``"name"``,
        and ``"arguments"`` keys.
    """
    calls: List[Dict[str, Any]] = []

    # Handle both object and dict formats
    if isinstance(response, dict):
        choices = response.get("choices", [])
    else:
        choices = getattr(response, "choices", [])

    for choice in choices:
        if isinstance(choice, dict):
            message = choice.get("message", {})
        else:
            message = getattr(choice, "message", None)
            if message is None:
                continue

        tool_calls = None
        if isinstance(message, dict):
            tool_calls = message.get("tool_calls")
        else:
            tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            continue

        for tc in tool_calls:
            if isinstance(tc, dict):
                func = tc.get("function", {})
                calls.append(
                    {
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "arguments": func.get("arguments", "{}"),
                    }
                )
            else:
                func = getattr(tc, "function", None)
                if func:
                    calls.append(
                        {
                            "id": getattr(tc, "id", ""),
                            "name": getattr(func, "name", ""),
                            "arguments": getattr(func, "arguments", "{}"),
                        }
                    )

    return calls


def parse_tool_arguments(arguments: str) -> Dict[str, Any]:
    """Parse tool call arguments from JSON string.

    Args:
        arguments: JSON string of tool arguments.

    Returns:
        Parsed arguments dictionary, or empty dict on failure.
    """
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except (json.JSONDecodeError, ValueError):
        result = parse_llm_json(arguments)
        return result if result is not None else {}


# =========================================================================
# Error classification
# =========================================================================

def classify_error(
    scores: Dict[str, float],
    case_entries: List[str],
    pims_result: Dict[str, Any],
) -> str:
    """Classify the error type for a task result.

    Categories:
        - ``correct``: all metrics pass
        - ``no_write``: agent never called write_case
        - ``missing_table``: agent missed required table(s)
        - ``wrong_column``: agent modified wrong column(s)
        - ``wrong_row``: correct tables but wrong rows
        - ``partial``: some components right, missed others
        - ``infeasible``: PIMS returned infeasible
        - ``other``: uncategorized

    Args:
        scores: Score dictionary from ``score_task()``.
        case_entries: Agent's CASE entries.
        pims_result: PIMS execution result.

    Returns:
        Error type string.
    """
    if not case_entries:
        return "no_write"

    pims_status = pims_result.get("status", "")
    if pims_status and "INFEASIBLE" in str(pims_status).upper():
        return "infeasible"

    row_r = scores.get("row_recall", 0)
    col_r = scores.get("col_recall", 0)
    match = scores.get("match", 0)
    table_f1 = scores.get("table_f1", 0)

    if match == 0 and row_r > 0:
        return "wrong_column"
    if match == 0 and row_r == 0 and table_f1 > 0:
        return "wrong_row"
    if 0 < match < 1.0:
        return "partial"
    if table_f1 >= 0.9 and match >= 0.9:
        return "correct"

    return "other"


# =========================================================================
# Logging setup
# =========================================================================

def setup_logging(
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    log_name: str = "skillrefine",
) -> logging.Logger:
    """Configure logging for SkillRefine experiments.

    Sets up a logger with console output and optional file output.

    Args:
        level: Logging level (default: ``logging.INFO``).
        log_dir: Optional directory for log files. If provided, creates
            a ``skillrefine.log`` file in this directory.
        log_name: Logger name.

    Returns:
        Configured logger instance.
    """
    log = logging.getLogger(log_name)
    log.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if log.handlers:
        return log

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    log.addHandler(console_handler)

    # File handler (optional)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "skillrefine.log", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        log.addHandler(file_handler)

    return log


# =========================================================================
# Message serialization
# =========================================================================

def serialize_messages(messages: list) -> list:
    """Serialize OpenAI message objects to JSON-safe dictionaries.

    Handles both dictionary and OpenAI Message object formats for
    logging and checkpoint purposes.

    Args:
        messages: List of OpenAI message objects or dictionaries.

    Returns:
        List of JSON-safe dictionaries.
    """
    serialized: List[Dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, dict):
            serialized.append(msg)
        else:
            entry: Dict[str, Any] = {"role": getattr(msg, "role", "unknown")}
            if hasattr(msg, "content") and msg.content:
                entry["content"] = str(msg.content)[:5000]
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


# =========================================================================
# Miscellaneous helpers
# =========================================================================

def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename.

    Args:
        name: Original string.

    Returns:
        Sanitized filename with only alphanumeric characters, hyphens,
        and underscores.
    """
    return re.sub(r"[^\w\-.]", "_", name)


def truncate_text(text: str, max_length: int = 5000, suffix: str = "...") -> str:
    """Truncate text to a maximum length.

    Args:
        text: Input text.
        max_length: Maximum length including suffix.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_objective_delta(actual: float, base: float) -> str:
    """Format an objective value delta for display.

    Args:
        actual: Actual objective value.
        base: Base objective value.

    Returns:
        Formatted delta string (e.g., ``"+200.47 (19.3%)"``).
    """
    delta = actual - base
    pct = (delta / base * 100) if base != 0 else 0
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f} ({sign}{pct:.1f}%)"
