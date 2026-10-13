"""Aspen PIMS COM automation client wrapper.

Provides a Pythonic interface to the Pimswin.Document COM server,
wrapping 174 IPims methods with robust error handling and context
manager support.

Usage::

    with AspenPIMS(suppress_ui=True) as pims:
        pims.open_model(r"C:\\models\\Weight Sample Experiment")
        pims.set_cases("001-003")
        pims.run_model()
        obj = pims.get_objective_value()
"""
from __future__ import annotations

import gc
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable, List, Optional

import win32com.client  # type: ignore


class AspenPIMS:
    """Thin wrapper around the Pimswin.Document COM server (174 IPims methods).

    Supports context manager protocol for automatic cleanup::

        with AspenPIMS(suppress_ui=True) as pims:
            pims.open_model(model_dir)
            ...

    Args:
        suppress_ui: If True, suppress PIMS UI dialogs after model opens.
        attach_existing: If True, attach to a running PIMS instance via
            ``GetActiveObject`` instead of launching a new one.
    """

    PROG_ID = "Pimswin.Document"

    def __init__(self, suppress_ui: bool = False, attach_existing: bool = False):
        if attach_existing:
            self.app = win32com.client.GetActiveObject(self.PROG_ID)
        else:
            self.app = win32com.client.Dispatch(self.PROG_ID)
        self._model_open = False
        self._model_folder = ""
        self._suppress_ui_pending = bool(suppress_ui)

    # ------------------------------------------------------------------ low-level

    def _invoke(self, name: str, *args: Any) -> Any:
        """Invoke a COM method by name, raising on non-callable attributes."""
        attr = getattr(self.app, name)
        if callable(attr):
            return attr(*args)
        if args:
            raise TypeError(f"COM member {name!r} is not callable but got args={args!r}")
        return attr

    def _safe_call(self, name: str, *args: Any) -> Any:
        """Invoke a COM method, returning None on any failure."""
        try:
            return self._invoke(name, *args)
        except Exception:
            return None

    # ------------------------------------------------------------------ info

    @property
    def version(self) -> str:
        """Full PIMS version string."""
        attr = self.app.GetVersion
        return str(attr() if callable(attr) else attr)

    @property
    def first_version(self) -> Any:
        """Major version number."""
        return self._invoke("GetFirstVersionNumber")

    @property
    def second_version(self) -> Any:
        """Minor version number."""
        return self._invoke("GetSecondVersionNumber")

    @property
    def third_version(self) -> Any:
        """Patch version number."""
        return self._invoke("GetThirdVersionNumber")

    # ------------------------------------------------------------------ lifecycle

    def open_model(self, model_folder: str) -> bool:
        """Open a PIMS model directory.

        Args:
            model_folder: Path to the PIMS model directory containing
                ``PimsModel.pimx`` and associated Excel workbooks.

        Returns:
            True on success.

        Raises:
            RuntimeError: If ``OpenModel`` returns False.
        """
        self._model_folder = str(model_folder)
        result = self.app.OpenModel(str(model_folder))
        success = bool(result) if result is not None else True
        if not success:
            raise RuntimeError(f"OpenModel returned False for: {model_folder}")
        self._model_open = True
        if self._suppress_ui_pending:
            self._safe_call("SetSuppressUserInterface", True)
            self._safe_call("SetDisplayMessageBox", False)
            self._suppress_ui_pending = False
        return success

    def open_model_ex(self, model_folder: str) -> None:
        """Open a PIMS model using the extended API (``OpenModelEx``).

        Args:
            model_folder: Path to the PIMS model directory.
        """
        self.app.OpenModelEx(str(model_folder))
        self._model_open = True

    def close_model(self) -> None:
        """Close the currently open model without quitting PIMS."""
        if self._model_open:
            try:
                self._invoke("CloseModel")
            finally:
                self._model_open = False

    def close_pims(self) -> None:
        """Quit PIMS and release the COM reference."""
        try:
            self._invoke("ClosePimsWin")
        finally:
            self._model_open = False
        try:
            del self.app
        except AttributeError:
            pass
        gc.collect()

    def save_model_file(self, save: bool = True) -> None:
        """Save the current model file.

        Args:
            save: If True, persist changes to disk.
        """
        self._invoke("SaveModelFile", bool(save))

    def update_model_tree(self) -> None:
        """Refresh the PIMS model tree view."""
        self._invoke("UpdateModelTree")

    def cleanup_model(self, name: str = "") -> None:
        """Run model cleanup.

        Args:
            name: Optional cleanup profile name.
        """
        self._invoke("CleanupModel", name)

    # ------------------------------------------------------------------ model state

    @property
    def is_model_open(self) -> bool:
        """Whether a model is currently open."""
        return self._model_open

    # ------------------------------------------------------------------ cases

    def get_cases_xml(self) -> str:
        """Retrieve the cases definition as XML.

        Returns:
            XML string of the cases block, or empty string on failure.
        """
        try:
            result = self.app.GetCases()
            if result:
                return str(result)
        except Exception:
            pass
        try:
            result = self.app.GetCases("")
            if result:
                return str(result)
        except Exception:
            pass
        return ""

    def _discover_cases_from_fs(self) -> List[str]:
        """Discover case numbers by scanning the model directory for artifacts."""
        patterns = (
            re.compile(r"^MODIF(\d{3})\.DAT$", re.IGNORECASE),
            re.compile(r"^!PDIST(\d{3})\.XLS$", re.IGNORECASE),
            re.compile(r"^!PGUESS(\d{3})\.XLS$", re.IGNORECASE),
            re.compile(r"^!ROWS(\d{3})\.XLS$", re.IGNORECASE),
            re.compile(r"^SolutionIndex(\d+)\.htm$", re.IGNORECASE),
        )
        found: set[str] = set()
        try:
            for name in os.listdir(self._model_folder):
                for p in patterns:
                    m = p.match(name)
                    if m:
                        num = m.group(1).lstrip("0") or "0"
                        found.add(num.zfill(3))
                        break
        except OSError:
            pass
        result = sorted(n for n in found if n.isdigit() and int(n) <= 999)
        if result:
            return result
        if os.path.isfile(os.path.join(self._model_folder, "PimsModel.pimx")):
            return [f"{i:03d}" for i in range(1, 8)]
        return []

    def list_case_numbers(self) -> List[str]:
        """List all case numbers in the open model.

        Attempts XML parsing first, falls back to filesystem discovery.

        Returns:
            Sorted list of zero-padded case number strings (e.g., ``["001", "002"]``).
        """
        try:
            xml = self.get_cases_xml()
        except Exception:
            xml = ""
        if xml:
            try:
                root = ET.fromstring(xml)
            except ET.ParseError:
                root = None
            if root is not None:
                numbers: set[str] = set()
                for node in root.iter():
                    num = node.get("Number") or node.get("CaseNumber") or node.get("Id")
                    if num and num.strip().isdigit():
                        numbers.add(num.strip().zfill(3))
                if numbers:
                    return sorted(numbers)
        return self._discover_cases_from_fs()

    def set_cases(self, spec: str) -> None:
        """Set the active case specification for solving.

        Args:
            spec: Case specification string, e.g., ``"001"`` or ``"001-003"``
                or ``"001,003,005"``.
        """
        self._invoke("SetCases", str(spec))

    def set_stack_all_cases(self, on: bool = True) -> None:
        """Enable or disable stacking all cases for batch solving.

        Args:
            on: If True, stack all cases.
        """
        self._invoke("SetStackAllCases", bool(on))

    def set_case_number(self, n: int) -> None:
        """Set the active case number for result retrieval.

        Args:
            n: Case number to activate.
        """
        self._invoke("SetCaseNumber", int(n))

    def get_selected_case_string(self) -> str:
        """Get the currently selected case description string."""
        return self._invoke("GetSelectedCaseString")

    def add_cases(self, xml_cases: str, table_name: str = "") -> None:
        """Add new cases from XML definition.

        Args:
            xml_cases: XML string defining cases to add.
            table_name: Optional table name context.
        """
        self._invoke("AddCases", xml_cases, table_name)

    def update_case_table(self, xml_cases: str, table_name: str = "") -> None:
        """Update an existing case table from XML.

        Args:
            xml_cases: XML string with updated case definitions.
            table_name: Optional table name context.
        """
        self._invoke("UpdateCaseTable", xml_cases, table_name)

    def set_case_comparison_name(self, name: str) -> None:
        """Set the case comparison display name.

        Args:
            name: Display name for case comparison.
        """
        self._invoke("SetCaseComparisonName", name)

    def run_case_comparison(self, first: int, last: int) -> None:
        """Run case comparison across a range.

        Args:
            first: First case number in range.
            last: Last case number in range.
        """
        self._invoke("RunCaseComparison", int(first), int(last))

    # ------------------------------------------------------------------ solver

    def run_model(self, show_dialog: bool = False) -> None:
        """Run the PIMS LP solver on the active cases.

        Args:
            show_dialog: If True, display the solver progress dialog.
        """
        self._invoke("RunModel", bool(show_dialog))

    def run_data_validation(self, show_dialog: bool = False) -> None:
        """Run data validation checks without solving.

        Args:
            show_dialog: If True, display the validation dialog.
        """
        self._invoke("RunDataValidation", bool(show_dialog))

    def run_all_cases(
        self, show_dialog: bool = False, use_stack: bool = False
    ) -> List[str]:
        """Run all discovered cases.

        Args:
            show_dialog: If True, display the solver progress dialog.
            use_stack: If True, use stack-all-cases mode instead of
                explicit case range.

        Returns:
            List of case numbers that were run.
        """
        cases = self.list_case_numbers()
        if use_stack or not cases:
            self.set_stack_all_cases(True)
            self.run_model(show_dialog)
            return cases
        spec = f"{cases[0]}-{cases[-1]}" if len(cases) > 1 else cases[0]
        self.set_cases(spec)
        self.run_model(show_dialog)
        return cases

    def run_parametric_analysis(
        self,
        case: int,
        input_solution: int,
        write_db: bool = False,
        generate: bool = False,
    ) -> None:
        """Run parametric analysis on a case.

        Args:
            case: Case number to analyze.
            input_solution: Input solution number.
            write_db: If True, write results to database.
            generate: If True, generate local models.
        """
        self._invoke(
            "RunParametricAnalysis",
            int(case),
            int(input_solution),
            bool(write_db),
            bool(generate),
        )

    # ------------------------------------------------------------------ results

    def get_objective_value(self) -> float:
        """Get the objective function value from the last solve.

        Returns:
            Objective function value (total profit/cost).
        """
        return self._invoke("GetObjectiveFunctionValue")

    def get_solution_status(self) -> str:
        """Get the solution status text from the last solve.

        Returns:
            Status string (e.g., ``"OPTIMAL"``, ``"INFEASIBLE"``).
        """
        return self._invoke("GetSolutionStatusText")

    def get_solution_recursion_passes(self) -> int:
        """Get the number of recursion passes used in the last solve."""
        return self._invoke("GetSolutionRecursionPasses")

    def get_solution_items_out_of_tolerance(self) -> int:
        """Get the count of items out of tolerance in the last solve."""
        return self._invoke("GetSolutionItemsOutOfTolerance")

    def get_last_run_id(self) -> Any:
        """Get the identifier of the last solver run."""
        return self._invoke("GetLastRunID")

    def get_last_solution_id(self) -> Any:
        """Get the identifier of the last solution."""
        return self._invoke("GetLastSolutionID")

    def get_purchases(self, case: int) -> Any:
        """Get purchase results for a case.

        Args:
            case: Case number.
        """
        return self._invoke("GetPurchases", int(case))

    def get_sales(self, case: int) -> Any:
        """Get sales results for a case.

        Args:
            case: Case number.
        """
        return self._invoke("GetSales", int(case))

    def get_capacities(self, case: int) -> Any:
        """Get capacity utilization results for a case.

        Args:
            case: Case number.
        """
        return self._invoke("GetCapacities", int(case))

    def get_process_limits(self, case: int) -> Any:
        """Get process limits results for a case.

        Args:
            case: Case number.
        """
        return self._invoke("GetProcessLimits", int(case))

    # ------------------------------------------------------------------ tables

    def get_table_list(self, model_name: str = "") -> Iterable[str]:
        """Get the list of assigned table names.

        Args:
            model_name: Optional model name override.

        Returns:
            Iterable of table name strings.
        """
        for call in (
            lambda: self.app.GetTableList(model_name),
            lambda: self.app.GetTableList(self._model_folder),
            lambda: self.app.GetTableList(),
        ):
            try:
                result = call()
                if result:
                    return result
            except Exception:
                continue
        return []

    def get_number_of_assigned_tables(self, table: str) -> int:
        """Get the number of assigned table files for a table.

        Args:
            table: Table name (e.g., ``"BUY"``).
        """
        return self._invoke("GetNumberOfAssignedTables", table)

    def is_table_enabled(self, table: str, n: int = 1) -> bool:
        """Check if a table assignment is enabled.

        Args:
            table: Table name.
            n: Assignment index (1-based).
        """
        return bool(self._invoke("IsTableEnabled", table, int(n)))

    def enable_table(self, table: str, n: int, on: bool) -> None:
        """Enable or disable a table assignment.

        Args:
            table: Table name.
            n: Assignment index (1-based).
            on: If True, enable; if False, disable.
        """
        self._invoke("EnableTable", table, int(n), bool(on))

    def enable_table_ex(self, model: str, table: str, n: int, on: bool) -> None:
        """Enable or disable a table assignment in a specific model.

        Args:
            model: Model name.
            table: Table name.
            n: Assignment index (1-based).
            on: If True, enable; if False, disable.
        """
        self._invoke("EnableTableEx", model, table, int(n), bool(on))

    def get_table_file(self, table: str, n: int = 1) -> str:
        """Get the Excel file path for a table assignment.

        Args:
            table: Table name.
            n: Assignment index (1-based).

        Returns:
            File path string.
        """
        return self._invoke("GetTableFile", table, int(n))

    def set_table_file(self, table: str, n: int, file: str, sheet: str) -> None:
        """Set the Excel file and sheet for a table assignment.

        Args:
            table: Table name (e.g., ``"BUY"``).
            n: Assignment index (0-based for first assignment).
            file: Path to the Excel workbook.
            sheet: Sheet name within the workbook.
        """
        self._invoke("SetTableFile", table, int(n), file, sheet)

    def get_table_sheet(self, table: str, n: int = 1) -> str:
        """Get the sheet name for a table assignment.

        Args:
            table: Table name.
            n: Assignment index (1-based).

        Returns:
            Sheet name string.
        """
        return self._invoke("GetTableSheet", table, int(n))

    def add_table_file(self, table: str, file: str, sheet: str) -> None:
        """Add a new table file assignment.

        Args:
            table: Table name.
            file: Path to the Excel workbook.
            sheet: Sheet name within the workbook.
        """
        self._invoke("AddTableFile", table, file, sheet)

    def remove_table_file(self, table: str, n: int) -> None:
        """Remove a table file assignment.

        Args:
            table: Table name.
            n: Assignment index to remove.
        """
        self._invoke("RemoveTableFile", table, int(n))

    def get_standard_table(self, table: str, model_name: str = "") -> Any:
        """Get standard table data.

        Args:
            table: Table name.
            model_name: Optional model name.
        """
        return self._invoke("GetStandardTable", table, model_name)

    def get_standard_table_ex(self, table: str, model_name: str = "") -> Any:
        """Get standard table data (extended format).

        Args:
            table: Table name.
            model_name: Optional model name.
        """
        return self._invoke("GetStandardTableEx", table, model_name)

    def get_raw_standard_table(self, table: str, model_name: str = "") -> Any:
        """Get raw standard table data without processing.

        Args:
            table: Table name.
            model_name: Optional model name.
        """
        return self._invoke("GetRawStandardTable", table, model_name)

    def suppress_all_spreadsheet_tables(self) -> None:
        """Suppress all spreadsheet-based table assignments."""
        self._invoke("SuppressAllSpreadsheetTables")

    def suppress_si_server(self, server: str, model: str, suppress: bool) -> None:
        """Suppress or enable an SI server.

        Args:
            server: Server name.
            model: Model name.
            suppress: If True, suppress the server.
        """
        self._invoke("SuppressSiServer", server, model, bool(suppress))

    # ------------------------------------------------------------------ settings

    def get_integer_setting(self, keyword: str) -> int:
        """Get an integer model setting.

        Args:
            keyword: Setting keyword name.
        """
        return self._invoke("GetIntegerSetting", keyword)

    def set_integer_setting(self, keyword: str, value: int) -> None:
        """Set an integer model setting.

        Args:
            keyword: Setting keyword name.
            value: Integer value to set.
        """
        self._invoke("SetIntegerSetting", keyword, int(value))

    def get_double_setting(self, keyword: str) -> float:
        """Get a floating-point model setting.

        Args:
            keyword: Setting keyword name.
        """
        return self._invoke("GetDoubleSetting", keyword)

    def set_double_setting(self, keyword: str, value: float) -> None:
        """Set a floating-point model setting.

        Args:
            keyword: Setting keyword name.
            value: Float value to set.
        """
        self._invoke("SetDoubleSetting", keyword, float(value))

    def get_string_setting(self, keyword: str) -> str:
        """Get a string model setting.

        Args:
            keyword: Setting keyword name.
        """
        return self._invoke("GetStringSetting", keyword)

    def set_string_setting(self, keyword: str, value: str) -> None:
        """Set a string model setting.

        Args:
            keyword: Setting keyword name.
            value: String value to set.
        """
        self._invoke("SetStringSetting", keyword, str(value))

    def get_date_setting(self, keyword: str) -> Any:
        """Get a date model setting.

        Args:
            keyword: Setting keyword name.
        """
        return self._invoke("GetDateSetting", keyword)

    def set_date_setting(self, keyword: str, value: Any) -> None:
        """Set a date model setting.

        Args:
            keyword: Setting keyword name.
            value: Date value to set.
        """
        self._invoke("SetDateSetting", keyword, value)

    def get_setting(self, keyword: str) -> Any:
        """Auto-detect and retrieve a setting by trying all type getters.

        Args:
            keyword: Setting keyword name.

        Returns:
            The setting value, or None if not found.
        """
        for getter in (
            self.app.GetIntegerSetting,
            self.app.GetDoubleSetting,
            self.app.GetStringSetting,
            self.app.GetDateSetting,
        ):
            try:
                return getter(keyword)
            except Exception:
                continue
        return None

    def set_setting(self, keyword: str, value: Any) -> None:
        """Auto-detect type and set a model setting.

        Args:
            keyword: Setting keyword name.
            value: Value to set (type is inferred from Python type).
        """
        if isinstance(value, bool):
            self.app.SetIntegerSetting(keyword, 1 if value else 0)
        elif isinstance(value, int):
            self.app.SetIntegerSetting(keyword, value)
        elif isinstance(value, float):
            self.app.SetDoubleSetting(keyword, value)
        else:
            self.app.SetStringSetting(keyword, str(value))

    # ------------------------------------------------------------------ solver controls

    def get_atol(self) -> float:
        """Get absolute tolerance."""
        return self._invoke("GetATol")

    def set_atol(self, v: float) -> None:
        """Set absolute tolerance."""
        self._invoke("SetATol", float(v))

    def get_rtol(self) -> float:
        """Get relative tolerance."""
        return self._invoke("GetRTol")

    def set_rtol(self, v: float) -> None:
        """Set relative tolerance."""
        self._invoke("SetRTol", float(v))

    def get_dtol(self) -> float:
        """Get degeneracy tolerance."""
        return self._invoke("GetDTol")

    def set_dtol(self, v: float) -> None:
        """Set degeneracy tolerance."""
        self._invoke("SetDTol", float(v))

    def get_max_pass(self) -> int:
        """Get maximum recursion passes."""
        return self._invoke("GetMaxPass")

    def set_max_pass(self, v: int) -> None:
        """Set maximum recursion passes."""
        self._invoke("SetMaxPass", int(v))

    def get_max_ipass(self) -> int:
        """Get maximum inner passes."""
        return self._invoke("GetMaxIPass")

    def set_max_ipass(self, v: int) -> None:
        """Set maximum inner passes."""
        self._invoke("SetMaxIPass", int(v))

    def get_max_pass1(self) -> int:
        """Get maximum first-stage passes."""
        return self._invoke("GetMaxPass1")

    def set_max_pass1(self, v: int) -> None:
        """Set maximum first-stage passes."""
        self._invoke("SetMaxPass1", int(v))

    def get_max_step(self) -> float:
        """Get maximum step size."""
        return self._invoke("GetMaxStep")

    def set_max_step(self, v: float) -> None:
        """Set maximum step size."""
        self._invoke("SetMaxStep", float(v))

    def get_min_obj(self) -> float:
        """Get minimum objective threshold."""
        return self._invoke("GetMinObj")

    def set_min_obj(self, v: float) -> None:
        """Set minimum objective threshold."""
        self._invoke("SetMinObj", float(v))

    def clear_min_obj(self) -> None:
        """Clear the minimum objective constraint."""
        self._invoke("ClearMinObj")

    def is_min_obj_on(self) -> bool:
        """Check if minimum objective constraint is active."""
        return bool(self._invoke("IsMinObjOn"))

    def is_fix_bal_on(self) -> bool:
        """Check if fixed balance mode is active."""
        return bool(self._invoke("IsFixBalOn"))

    def set_fix_bal(self, on: bool) -> None:
        """Enable or disable fixed balance mode."""
        self._invoke("SetFixBal", bool(on))

    def is_fix_bal_on_g(self) -> bool:
        """Check if fixed balance on G is active."""
        return bool(self._invoke("IsFixBalOnG"))

    def set_fix_bal_on_g(self, on: bool) -> None:
        """Enable or disable fixed balance on G."""
        self._invoke("SetFixBalOnG", bool(on))

    def set_solve_on(self, on: bool) -> None:
        """Enable or disable solving."""
        self._invoke("SetSolveOn", bool(on))

    def set_generate_on(self, on: bool) -> None:
        """Enable or disable matrix generation."""
        self._invoke("SetGenerateOn", bool(on))

    def set_generate_local_models(self, on: bool) -> None:
        """Enable or disable local model generation."""
        self._invoke("SetGenerateLocalModels", bool(on))

    def set_model_type(self, n: int) -> None:
        """Set the model type.

        Args:
            n: Model type integer.
        """
        self._invoke("SetModelType", int(n))

    # ------------------------------------------------------------------ metadata

    def get_model_title(self) -> str:
        """Get the model title."""
        return self._invoke("GetModelTitle")

    def set_model_title(self, s: str) -> None:
        """Set the model title."""
        self._invoke("SetModelTitle", s)

    def get_time_text(self) -> str:
        """Get the time period text."""
        return self._invoke("GetTimeText")

    def set_time_text(self, s: str) -> None:
        """Set the time period text."""
        self._invoke("SetTimeText", s)

    def get_note(self, n: int) -> str:
        """Get a model note by index.

        Args:
            n: Note index.
        """
        return self._invoke("GetNote", int(n))

    def set_note(self, note: str, n: int) -> None:
        """Set a model note by index.

        Args:
            note: Note text.
            n: Note index.
        """
        self._invoke("SetNote", note, int(n))

    def get_user_control(self) -> bool:
        """Check if user control mode is active."""
        return bool(self._invoke("GetUserControl"))

    def set_user_control(self, on: bool) -> None:
        """Enable or disable user control mode."""
        self._invoke("SetUserControl", bool(on))

    def get_p1(self) -> float:
        """Get parameter P1."""
        return self._invoke("GetP1")

    def set_p1(self, v: float) -> None:
        """Set parameter P1."""
        self._invoke("SetP1", float(v))

    def get_p2(self) -> float:
        """Get parameter P2."""
        return self._invoke("GetP2")

    def set_p2(self, v: float) -> None:
        """Set parameter P2."""
        self._invoke("SetP2", float(v))

    def get_p3(self) -> float:
        """Get parameter P3."""
        return self._invoke("GetP3")

    def set_p3(self, v: float) -> None:
        """Set parameter P3."""
        self._invoke("SetP3", float(v))

    def get_p4(self) -> float:
        """Get parameter P4."""
        return self._invoke("GetP4")

    def set_p4(self, v: float) -> None:
        """Set parameter P4."""
        self._invoke("SetP4", float(v))

    # ------------------------------------------------------------------ matrix info

    def get_lp_matrix_rows(self) -> int:
        """Get LP matrix row count."""
        return self._invoke("GetLPMatrixRows")

    def set_lp_matrix_rows(self, v: int) -> None:
        """Set LP matrix row count."""
        self._invoke("SetLPMatrixRows", int(v))

    def get_lp_matrix_columns(self) -> int:
        """Get LP matrix column count."""
        return self._invoke("GetLPMatrixColumns")

    def set_lp_matrix_columns(self, v: int) -> None:
        """Set LP matrix column count."""
        self._invoke("SetLPMatrixColumns", int(v))

    def get_lp_non_zeros(self) -> int:
        """Get LP non-zero element count."""
        return self._invoke("GetLPNonZeros")

    def set_lp_non_zeros(self, v: int) -> None:
        """Set LP non-zero element count."""
        self._invoke("SetLPNonZeros", int(v))

    def get_table_rows(self) -> int:
        """Get table row count."""
        return self._invoke("GetTableRows")

    def set_table_rows(self, v: int) -> None:
        """Set table row count."""
        self._invoke("SetTableRows", int(v))

    def get_table_columns(self) -> int:
        """Get table column count."""
        return self._invoke("GetTableColumns")

    def set_table_columns(self, v: int) -> None:
        """Set table column count."""
        self._invoke("SetTableColumns", int(v))

    def get_table_row_columns(self) -> int:
        """Get table row-column count."""
        return self._invoke("GetTableRowColumns")

    def set_table_row_columns(self, v: int) -> None:
        """Set table row-column count."""
        self._invoke("SetTableRowColumns", int(v))

    def get_recursed_items(self) -> int:
        """Get recursed item count."""
        return self._invoke("GetRecursedItems")

    def set_recursed_items(self, v: int) -> None:
        """Set recursed item count."""
        self._invoke("SetRecursedItems", int(v))

    def get_recursed_coefficients(self) -> int:
        """Get recursed coefficient count."""
        return self._invoke("GetRecursedCoefficients")

    def set_recursed_coefficients(self, v: int) -> None:
        """Set recursed coefficient count."""
        self._invoke("SetRecursedCoefficients", int(v))

    def get_rec_invsp(self, model: str = "") -> int:
        """Get recursion inventory count."""
        return self._invoke("GetRecInvsp", model)

    def set_rec_invsp(self, model: str, v: int) -> None:
        """Set recursion inventory count."""
        self._invoke("SetRecInvsp", model, int(v))

    # ------------------------------------------------------------------ database

    def get_database_model_id(self) -> int:
        """Get database model ID."""
        return self._invoke("GetDatabaseModelID")

    def set_database_model_id(self, n: int) -> None:
        """Set database model ID."""
        self._invoke("SetDatabaseModelID", int(n))

    def get_database_output_format(self) -> str:
        """Get database output format."""
        return self._invoke("GetDatabaseOutputFormat")

    def set_database_output_format(self, fmt: str) -> None:
        """Set database output format."""
        self._invoke("SetDatabaseOutputFormat", fmt)

    def get_output_database_file_path(self) -> str:
        """Get output database file path."""
        return self._invoke("GetOutputDatabaseFilePath")

    def set_compact_database(self, on: bool) -> None:
        """Enable or disable database compaction."""
        self._invoke("SetCompactDatabase", bool(on))

    def set_database_description(self, desc: str) -> None:
        """Set database description."""
        self._invoke("SetDatabaseDescription", desc)

    # ------------------------------------------------------------------ UI controls

    def set_display_message_box(self, on: bool) -> None:
        """Enable or disable PIMS message boxes.

        Args:
            on: If True, show message boxes; if False, suppress them.
        """
        self._invoke("SetDisplayMessageBox", bool(on))

    def set_suppress_user_interface(self, flag: bool) -> None:
        """Enable or disable UI suppression for headless operation.

        Args:
            flag: If True, suppress all UI elements.
        """
        self._invoke("SetSuppressUserInterface", bool(flag))

    def set_window_placement(self, cmd: int) -> None:
        """Set the PIMS window placement.

        Args:
            cmd: Window placement command (Win32 ``SW_*`` constants).
        """
        self._invoke("SetWindowPlacement", int(cmd))

    def set_use_pm_colnames(self, on: bool) -> None:
        """Enable or disable PM-style column names."""
        self._invoke("SetUsePMColnames", bool(on))

    # ------------------------------------------------------------------ context manager

    def __enter__(self) -> "AspenPIMS":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self.close_model()
        finally:
            self.close_pims()


def variant_to_rows(variant: Any) -> List[Any]:
    """Normalize a COM SAFEARRAY or nested tuple into a flat list of rows.

    Args:
        variant: COM variant value (may be a SAFEARRAY, tuple, or scalar).

    Returns:
        List of rows, where each row is a list of values.
    """
    if variant is None:
        return []
    try:
        rows = list(variant)
    except TypeError:
        return [variant]
    out = []
    for r in rows:
        if r is None:
            continue
        if isinstance(r, (list, tuple)):
            out.append(list(r))
        else:
            out.append([r])
    return out
