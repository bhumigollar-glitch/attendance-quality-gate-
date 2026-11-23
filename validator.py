"""
validator.py
============
Data quality validation engine for Attendance Spreadsheet Quality Gate.

Validation Rules:
- Rule 1: Missing Values (identify missing required fields: Student ID, Subject, Classes Held, Classes Attended)
- Rule 2: Duplicate Records (identify repeated student + subject/session combinations; legitimate multiple classes allowed)
- Rule 3: Invalid Attendance Counts (negative present count, negative classes held, present > held, non-numeric values)
- Rule 4: Attendance Percentage Validation (calculate expected = (attended / held) * 100, compare with reported, handle 0 held)
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import io
import math
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# Column alias dictionary for intelligent column mapping
DEFAULT_COLUMN_ALIASES: Dict[str, List[str]] = {
    "student_id": [
        "student id", "studentid", "student_id", "usn", "roll no",
        "roll number", "roll_no", "registration no", "reg no", "id", "admission no"
    ],
    "student_name": [
        "student name", "student_name", "name", "full name", "candidate name"
    ],
    "subject": [
        "subject", "subject code", "subject_code", "course", "course code",
        "course name", "subject name", "module", "paper"
    ],
    "session_date": [
        "date", "session date", "session", "class date", "session id",
        "period", "slot", "semester"
    ],
    "classes_held": [
        "classes held", "classes_held", "total classes", "total_classes",
        "held", "conducted", "total sessions", "sessions held", "total conducted"
    ],
    "classes_attended": [
        "classes attended", "classes_attended", "attended", "present",
        "present count", "attendance count", "total attended", "sessions attended"
    ],
    "attendance_percentage": [
        "attendance %", "attendance percentage", "attendance_percentage",
        "percentage", "percent", "%", "attendance_percent", "attendance pct"
    ],
}


@dataclass
class ValidationIssue:
    row_number: int  # 1-indexed spreadsheet row number (Row 1 is header, data starts at Row 2)
    student_id: str
    issue_type: str
    explanation: str
    severity: str  # "Error" or "Warning"
    suggested_action: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Row Number": self.row_number,
            "Student ID": self.student_id,
            "Issue Type": self.issue_type,
            "Explanation": self.explanation,
            "Severity": self.severity,
            "Suggested Action": self.suggested_action,
        }


@dataclass
class ValidationSummary:
    total_records: int
    total_issues: int
    total_errors: int
    total_warnings: int
    quality_gate_passed: bool
    status_label: str  # "PASSED", "PASSED WITH WARNINGS", "FAILED"
    issues_by_category: Dict[str, int]
    issues_by_severity: Dict[str, int]


class AttendanceValidator:
    """
    Validates attendance spreadsheets against data quality rules.
    Non-destructive: original DataFrame is preserved unchanged.
    """

    def __init__(
        self,
        column_mapping: Optional[Dict[str, str]] = None,
        percentage_tolerance: float = 0.5,
        duplicate_key_columns: Optional[List[str]] = None,
    ):
        """
        Args:
            column_mapping: Dict mapping standard names ('student_id', 'subject', etc.)
                           to actual DataFrame column names.
            percentage_tolerance: Max difference (%) between reported and expected before flagging.
            duplicate_key_columns: List of standard column names that define a duplicate record.
        """
        self.column_mapping = column_mapping or {}
        self.percentage_tolerance = percentage_tolerance
        self.duplicate_key_columns = duplicate_key_columns

    @staticmethod
    def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Automatically maps spreadsheet columns to standard semantic fields
        using case-insensitive alias matching.
        """
        mapping: Dict[str, Optional[str]] = {key: None for key in DEFAULT_COLUMN_ALIASES}
        raw_cols = list(df.columns)
        normalized_cols = {str(c).strip().lower(): c for c in raw_cols}

        for standard_key, aliases in DEFAULT_COLUMN_ALIASES.items():
            for alias in aliases:
                # Check exact match first
                if alias in normalized_cols:
                    mapping[standard_key] = normalized_cols[alias]
                    break
            # If no exact match, check substring/contains
            if mapping[standard_key] is None:
                for norm_name, original_col in normalized_cols.items():
                    if any(alias in norm_name for alias in aliases):
                        mapping[standard_key] = original_col
                        break

        return mapping

    @staticmethod
    def is_blank(value: Any) -> bool:
        """Checks if a cell value is missing, NaN, empty string, or whitespace."""
        if value is None:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        if pd.isna(value):
            return True
        val_str = str(value).strip().lower()
        if val_str in ("", "nan", "null", "none", "n/a", "-", "na"):
            return True
        return False

    @staticmethod
    def parse_numeric(value: Any) -> Tuple[Optional[float], bool]:
        """
        Attempts to parse a value as float.
        Returns (parsed_value, is_valid).
        """
        if AttendanceValidator.is_blank(value):
            return None, True  # Handled by missing value check
        if isinstance(value, (int, float)):
            if math.isnan(value):
                return None, True
            return float(value), True
        try:
            val_str = str(value).strip().replace(",", "")
            return float(val_str), True
        except (ValueError, TypeError):
            return None, False

    @staticmethod
    def parse_percentage(value: Any) -> Tuple[Optional[float], bool]:
        """
        Parses percentage value which might be formatted as '75%', '0.75', or '75.0'.
        Normalizes into a 0.0 - 100.0 scale.
        """
        if AttendanceValidator.is_blank(value):
            return None, True
        if isinstance(value, (int, float)):
            num = float(value)
            # If value is <= 1.0 and > 0, it might be decimal representation e.g. 0.85 -> 85%
            # But note: 1% is 1.0, 0% is 0.0. Usually if entered as 0.75 in Excel formatted as %
            if 0 < num <= 1.0:
                num = num * 100.0
            return num, True
        try:
            val_str = str(value).strip().replace("%", "").replace(",", "")
            num = float(val_str)
            if 0 < num <= 1.0:
                num = num * 100.0
            return num, True
        except (ValueError, TypeError):
            return None, False

    def validate(
        self,
        df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, Optional[str]]] = None,
    ) -> Tuple[List[ValidationIssue], ValidationSummary]:
        """
        Executes all 4 validation rules on the given attendance DataFrame.

        Returns:
            Tuple of (list of ValidationIssue objects, ValidationSummary object)
        """
        # Determine active column mapping
        effective_mapping = self.detect_columns(df)
        if custom_mapping:
            for k, v in custom_mapping.items():
                if v is not None:
                    effective_mapping[k] = v

        id_col = effective_mapping.get("student_id")
        subject_col = effective_mapping.get("subject")
        session_col = effective_mapping.get("session_date")
        held_col = effective_mapping.get("classes_held")
        attended_col = effective_mapping.get("classes_attended")
        pct_col = effective_mapping.get("attendance_percentage")

        issues: List[ValidationIssue] = []
        total_records = len(df)

        # ----------------------------------------------------
        # Rule 1 & Rule 3 & Rule 4: Row-by-Row Validation
        # ----------------------------------------------------
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel row index (header is 1, data starts at 2)

            # Get Student ID identifier
            raw_id = row[id_col] if id_col and id_col in df.columns else None
            student_id_str = "[Missing]" if self.is_blank(raw_id) else str(raw_id).strip()

            # Rule 1: Missing Required Fields
            # Student ID
            if id_col and self.is_blank(row[id_col]):
                issues.append(
                    ValidationIssue(
                        row_number=row_num,
                        student_id="[Missing]",
                        issue_type="Missing Value",
                        explanation=f"Missing required Student ID in column '{id_col}'.",
                        severity="Error",
                        suggested_action="Provide the missing Student ID from official enrollment records.",
                    )
                )

            # Subject
            if subject_col and self.is_blank(row[subject_col]):
                issues.append(
                    ValidationIssue(
                        row_number=row_num,
                        student_id=student_id_str,
                        issue_type="Missing Value",
                        explanation=f"Missing required Subject/Course name in column '{subject_col}'.",
                        severity="Error",
                        suggested_action="Specify the subject or course code for this attendance record.",
                    )
                )

            # Classes Held missing check
            held_is_blank = False
            if held_col:
                if self.is_blank(row[held_col]):
                    held_is_blank = True
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Missing Value",
                            explanation=f"Missing required count for Classes Held in column '{held_col}'.",
                            severity="Error",
                            suggested_action="Enter the total number of classes conducted.",
                        )
                    )

            # Classes Attended missing check
            attended_is_blank = False
            if attended_col:
                if self.is_blank(row[attended_col]):
                    attended_is_blank = True
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Missing Value",
                            explanation=f"Missing required count for Classes Attended in column '{attended_col}'.",
                            severity="Error",
                            suggested_action="Enter the student's present attendance count.",
                        )
                    )

            # Rule 3: Invalid Attendance Counts
            parsed_held, held_valid = None, False
            if held_col and not held_is_blank:
                parsed_held, held_valid = self.parse_numeric(row[held_col])
                if not held_valid:
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Invalid Attendance Count",
                            explanation=f"Non-numeric value '{row[held_col]}' in '{held_col}'.",
                            severity="Error",
                            suggested_action="Replace the non-numeric entry with an integer count.",
                        )
                    )
                elif parsed_held is not None and parsed_held < 0:
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Invalid Attendance Count",
                            explanation=f"Classes held ({parsed_held:g}) is negative. Total classes held cannot be less than 0.",
                            severity="Error",
                            suggested_action="Correct negative classes held to a valid non-negative integer.",
                        )
                    )

            parsed_attended, attended_valid = None, False
            if attended_col and not attended_is_blank:
                parsed_attended, attended_valid = self.parse_numeric(row[attended_col])
                if not attended_valid:
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Invalid Attendance Count",
                            explanation=f"Non-numeric value '{row[attended_col]}' in '{attended_col}'.",
                            severity="Error",
                            suggested_action="Replace the non-numeric entry with an integer count.",
                        )
                    )
                elif parsed_attended is not None and parsed_attended < 0:
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Invalid Attendance Count",
                            explanation=f"Present count ({parsed_attended:g}) is negative. Attendance count cannot be less than 0.",
                            severity="Error",
                            suggested_action="Correct negative present count to a valid non-negative integer.",
                        )
                    )

            # Present count exceeds classes held
            if (
                held_valid
                and attended_valid
                and parsed_held is not None
                and parsed_attended is not None
                and parsed_held >= 0
                and parsed_attended >= 0
            ):
                if parsed_attended > parsed_held:
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Invalid Attendance Count",
                            explanation=(
                                f"Present count ({parsed_attended:g}) exceeds classes held ({parsed_held:g}). "
                                "A student cannot attend more classes than were conducted."
                            ),
                            severity="Error",
                            suggested_action="Verify attendance logs; adjust present count to be <= classes held.",
                        )
                    )

            # Rule 4: Attendance Percentage Validation
            if pct_col and pct_col in df.columns:
                raw_pct = row[pct_col]
                if self.is_blank(raw_pct):
                    # Flag blank percentage as Warning
                    if held_valid and parsed_held is not None and parsed_held > 0:
                        issues.append(
                            ValidationIssue(
                                row_number=row_num,
                                student_id=student_id_str,
                                issue_type="Missing Value",
                                explanation=f"Reported Attendance Percentage column '{pct_col}' is blank.",
                                severity="Warning",
                                suggested_action="Calculate and populate attendance percentage: (Attended / Held) * 100.",
                            )
                        )
                else:
                    parsed_pct, pct_valid = self.parse_percentage(raw_pct)
                    if not pct_valid:
                        issues.append(
                            ValidationIssue(
                                row_number=row_num,
                                student_id=student_id_str,
                                issue_type="Percentage Mismatch",
                                explanation=f"Invalid percentage format '{raw_pct}' in column '{pct_col}'.",
                                severity="Warning",
                                suggested_action="Provide percentage as a valid numerical percentage (e.g. 85.5% or 85.5).",
                            )
                        )
                    elif (
                        held_valid
                        and attended_valid
                        and parsed_held is not None
                        and parsed_attended is not None
                        and parsed_pct is not None
                    ):
                        if parsed_held == 0:
                            # Handle zero classes held separately
                            if parsed_pct != 0:
                                issues.append(
                                    ValidationIssue(
                                        row_number=row_num,
                                        student_id=student_id_str,
                                        issue_type="Percentage Mismatch",
                                        explanation=(
                                            f"Classes held is 0, but reported percentage is {parsed_pct:g}%. "
                                            "Expected percentage is 0.0% when 0 classes have been conducted."
                                        ),
                                        severity="Warning",
                                        suggested_action="Set attendance percentage to 0.0% or N/A when no classes were held.",
                                    )
                                )
                        elif parsed_held > 0 and 0 <= parsed_attended <= parsed_held:
                            expected_pct = (parsed_attended / parsed_held) * 100.0
                            diff = abs(parsed_pct - expected_pct)
                            if diff > self.percentage_tolerance:
                                issues.append(
                                    ValidationIssue(
                                        row_number=row_num,
                                        student_id=student_id_str,
                                        issue_type="Percentage Mismatch",
                                        explanation=(
                                            f"Reported attendance percentage ({parsed_pct:.1f}%) does not match expected "
                                            f"calculated percentage ({expected_pct:.1f}% based on {parsed_attended:g} / {parsed_held:g} classes)."
                                        ),
                                        severity="Warning",
                                        suggested_action=(
                                            f"Update percentage to {expected_pct:.1f}% using formula: "
                                            "(Classes Attended / Classes Held) * 100."
                                        ),
                                    )
                                )

        # ----------------------------------------------------
        # Rule 2: Duplicate Detection
        # ----------------------------------------------------
        # Key combination: Student ID + Subject (+ Session/Date if available)
        # Note from specification: "A student appearing in multiple legitimate classes
        # should not be flagged simply because their ID appears more than once."
        key_cols: List[str] = []
        if self.duplicate_key_columns:
            key_cols = [c for c in self.duplicate_key_columns if c in df.columns]
        else:
            if id_col and id_col in df.columns:
                key_cols.append(id_col)
            if subject_col and subject_col in df.columns:
                key_cols.append(subject_col)
            if session_col and session_col in df.columns:
                key_cols.append(session_col)

        if len(key_cols) >= 2:
            seen_keys: Dict[Tuple[str, ...], int] = {}  # key -> first_row_number
            for idx, row in df.iterrows():
                row_num = idx + 2
                raw_id = row[id_col] if id_col and id_col in df.columns else None
                student_id_str = "[Missing]" if self.is_blank(raw_id) else str(raw_id).strip()

                # Build record key tuple normalized
                key_parts = []
                has_blank_in_key = False
                for c in key_cols:
                    val = row[c]
                    if self.is_blank(val):
                        has_blank_in_key = True
                        break
                    key_parts.append(str(val).strip().lower())

                # If key components are missing, Rule 1 handles it, do not treat as duplicate
                if has_blank_in_key or not key_parts:
                    continue

                composite_key = tuple(key_parts)
                if composite_key in seen_keys:
                    first_row = seen_keys[composite_key]
                    key_desc = ", ".join(f"{c}='{row[c]}'" for c in key_cols)
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            student_id=student_id_str,
                            issue_type="Duplicate Record",
                            explanation=(
                                f"Duplicate record detected for combination ({key_desc}). "
                                f"Matches earlier record at Row {first_row}."
                            ),
                            severity="Warning",
                            suggested_action=(
                                f"Investigate duplicate entry with Row {first_row}. "
                                "Merge or remove redundant record if unintentional."
                            ),
                        )
                    )
                else:
                    seen_keys[composite_key] = row_num

        # Sort issues by Row Number
        issues.sort(key=lambda x: (x.row_number, 0 if x.severity == "Error" else 1))

        # ----------------------------------------------------
        # Summary Computation
        # ----------------------------------------------------
        total_errors = sum(1 for i in issues if i.severity == "Error")
        total_warnings = sum(1 for i in issues if i.severity == "Warning")
        total_issues = len(issues)

        issues_by_category: Dict[str, int] = {}
        for i in issues:
            issues_by_category[i.issue_type] = issues_by_category.get(i.issue_type, 0) + 1

        issues_by_severity = {
            "Error": total_errors,
            "Warning": total_warnings,
        }

        if total_errors == 0 and total_warnings == 0:
            status_label = "PASSED"
            gate_passed = True
        elif total_errors == 0:
            status_label = "PASSED WITH WARNINGS"
            gate_passed = True
        else:
            status_label = "FAILED"
            gate_passed = False

        summary = ValidationSummary(
            total_records=total_records,
            total_issues=total_issues,
            total_errors=total_errors,
            total_warnings=total_warnings,
            quality_gate_passed=gate_passed,
            status_label=status_label,
            issues_by_category=issues_by_category,
            issues_by_severity=issues_by_severity,
        )

        return issues, summary

    @staticmethod
    def generate_excel_report(
        df_original: pd.DataFrame,
        issues: List[ValidationIssue],
        summary: ValidationSummary,
        file_name: str = "Uploaded Attendance",
    ) -> io.BytesIO:
        """
        Generates an Excel workbook (.xlsx) with:
        - Sheet 1: Quality Gate Summary
        - Sheet 2: Detected Issues (with color-coded severity badges and auto-fit columns)
        - Sheet 3: Full Annotated Data
        """
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # Style definitions - High Contrast Executive Theme
        title_font = Font(name="Calibri", size=16, bold=True, color="000000")
        subtitle_font = Font(name="Calibri", size=11, italic=True, color="555555")
        section_font = Font(name="Calibri", size=12, bold=True, color="000000")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        bold_font = Font(name="Calibri", size=11, bold=True, color="000000")
        regular_font = Font(name="Calibri", size=11, color="000000")
        
        header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
        error_fill = PatternFill(start_color="F2DEDE", end_color="F2DEDE", fill_type="solid")  # soft high-contrast red
        warning_fill = PatternFill(start_color="FCF8E3", end_color="FCF8E3", fill_type="solid") # soft amber
        pass_fill = PatternFill(start_color="DFF0D8", end_color="DFF0D8", fill_type="solid")    # soft green
        zebra_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")

        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC"),
        )

        # ----------------------------------------------------
        # Sheet 1: Quality Gate Summary
        # ----------------------------------------------------
        ws_sum = wb.create_sheet(title="Quality Gate Summary")
        ws_sum.views.sheetView[0].showGridLines = True

        ws_sum["A1"] = "Attendance Spreadsheet Quality Gate"
        ws_sum["A1"].font = title_font
        ws_sum["A2"] = f"Validation Report for: {file_name}"
        ws_sum["A2"].font = subtitle_font

        # Status Banner
        ws_sum["A4"] = "Quality Gate Status:"
        ws_sum["A4"].font = bold_font
        ws_sum["B4"] = summary.status_label
        ws_sum["B4"].font = Font(name="Calibri", size=12, bold=True)
        if summary.status_label == "PASSED":
            ws_sum["B4"].fill = pass_fill
        elif summary.status_label == "PASSED WITH WARNINGS":
            ws_sum["B4"].fill = warning_fill
        else:
            ws_sum["B4"].fill = error_fill

        # Summary Metrics Table
        ws_sum["A6"] = "Validation Metrics"
        ws_sum["A6"].font = section_font

        metrics = [
            ("Total Records Examined", summary.total_records),
            ("Total Issues Detected", summary.total_issues),
            ("Errors (Must Fix)", summary.total_errors),
            ("Warnings (Review Required)", summary.total_warnings),
        ]

        ws_sum["A7"] = "Metric"
        ws_sum["B7"] = "Value"
        ws_sum["A7"].font = header_font
        ws_sum["B7"].font = header_font
        ws_sum["A7"].fill = header_fill
        ws_sum["B7"].fill = header_fill

        for idx, (metric, val) in enumerate(metrics, start=8):
            ws_sum[f"A{idx}"] = metric
            ws_sum[f"B{idx}"] = val
            ws_sum[f"A{idx}"].font = regular_font
            ws_sum[f"B{idx}"].font = bold_font
            ws_sum[f"A{idx}"].border = thin_border
            ws_sum[f"B{idx}"].border = thin_border

        # Category Breakdown Table
        start_cat_row = 14
        ws_sum[f"A{start_cat_row}"] = "Issues by Category"
        ws_sum[f"A{start_cat_row}"].font = section_font

        ws_sum[f"A{start_cat_row+1}"] = "Category"
        ws_sum[f"B{start_cat_row+1}"] = "Count"
        ws_sum[f"A{start_cat_row+1}"].font = header_font
        ws_sum[f"B{start_cat_row+1}"].font = header_font
        ws_sum[f"A{start_cat_row+1}"].fill = header_fill
        ws_sum[f"B{start_cat_row+1}"].fill = header_fill

        curr_r = start_cat_row + 2
        if summary.issues_by_category:
            for cat, count in summary.issues_by_category.items():
                ws_sum[f"A{curr_r}"] = cat
                ws_sum[f"B{curr_r}"] = count
                ws_sum[f"A{curr_r}"].font = regular_font
                ws_sum[f"B{curr_r}"].font = regular_font
                ws_sum[f"A{curr_r}"].border = thin_border
                ws_sum[f"B{curr_r}"].border = thin_border
                curr_r += 1
        else:
            ws_sum[f"A{curr_r}"] = "No issues detected"
            ws_sum[f"B{curr_r}"] = 0
            ws_sum[f"A{curr_r}"].font = regular_font
            ws_sum[f"B{curr_r}"].font = regular_font
            ws_sum[f"A{curr_r}"].border = thin_border
            ws_sum[f"B{curr_r}"].border = thin_border

        ws_sum.column_dimensions["A"].width = 32
        ws_sum.column_dimensions["B"].width = 24

        # ----------------------------------------------------
        # Sheet 2: Detected Issues
        # ----------------------------------------------------
        ws_issues = wb.create_sheet(title="Detected Issues")
        ws_issues.views.sheetView[0].showGridLines = True

        issue_headers = [
            "Row Number",
            "Student ID",
            "Issue Type",
            "Severity",
            "Explanation",
            "Suggested Action",
        ]

        for col_idx, header in enumerate(issue_headers, start=1):
            cell = ws_issues.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws_issues.row_dimensions[1].height = 26

        if issues:
            for row_idx, issue in enumerate(issues, start=2):
                r_num_cell = ws_issues.cell(row=row_idx, column=1, value=issue.row_number)
                stu_cell = ws_issues.cell(row=row_idx, column=2, value=issue.student_id)
                type_cell = ws_issues.cell(row=row_idx, column=3, value=issue.issue_type)
                sev_cell = ws_issues.cell(row=row_idx, column=4, value=issue.severity)
                exp_cell = ws_issues.cell(row=row_idx, column=5, value=issue.explanation)
                act_cell = ws_issues.cell(row=row_idx, column=6, value=issue.suggested_action)

                for cell in (r_num_cell, stu_cell, type_cell, sev_cell, exp_cell, act_cell):
                    cell.font = regular_font
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical="center")

                r_num_cell.alignment = Alignment(horizontal="center", vertical="center")
                sev_cell.alignment = Alignment(horizontal="center", vertical="center")
                sev_cell.font = bold_font

                if issue.severity == "Error":
                    sev_cell.fill = error_fill
                else:
                    sev_cell.fill = warning_fill

                if row_idx % 2 == 1:
                    for cell in (r_num_cell, stu_cell, type_cell, exp_cell, act_cell):
                        cell.fill = zebra_fill
        else:
            empty_cell = ws_issues.cell(row=2, column=1, value="No data-quality issues detected in this file.")
            empty_cell.font = Font(name="Calibri", size=11, italic=True)

        # Auto-adjust column widths for issues sheet
        col_widths = {1: 14, 2: 18, 3: 26, 4: 14, 5: 50, 6: 45}
        for col_idx, width in col_widths.items():
            ws_issues.column_dimensions[get_column_letter(col_idx)].width = width

        # ----------------------------------------------------
        # Sheet 3: Full Annotated Data
        # ----------------------------------------------------
        ws_data = wb.create_sheet(title="Annotated Records")
        ws_data.views.sheetView[0].showGridLines = True

        # Map row issues by row_number
        row_issues_map: Dict[int, List[str]] = {}
        for issue in issues:
            row_issues_map.setdefault(issue.row_number, []).append(
                f"[{issue.severity}] {issue.issue_type}: {issue.explanation}"
            )

        data_headers = list(df_original.columns) + ["Gate Status", "Detected Notes"]
        for col_idx, header in enumerate(data_headers, start=1):
            cell = ws_data.cell(row=1, column=col_idx, value=str(header))
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws_data.row_dimensions[1].height = 24

        for row_idx, (_, row) in enumerate(df_original.iterrows(), start=2):
            excel_row = row_idx
            has_issues = excel_row in row_issues_map
            status_text = "Has Issues" if has_issues else "Valid"
            notes_text = " | ".join(row_issues_map[excel_row]) if has_issues else "Passed all quality checks"

            # Write original columns
            col_pos = 1
            for col_val in row:
                c = ws_data.cell(row=row_idx, column=col_pos, value=col_val if pd.notna(col_val) else "")
                c.font = regular_font
                c.border = thin_border
                col_pos += 1

            # Status cell
            stat_c = ws_data.cell(row=row_idx, column=col_pos, value=status_text)
            stat_c.font = bold_font
            stat_c.border = thin_border
            stat_c.alignment = Alignment(horizontal="center")
            if has_issues:
                # Check if error or warning
                has_error = any("Error" in n for n in row_issues_map[excel_row])
                stat_c.fill = error_fill if has_error else warning_fill
            else:
                stat_c.fill = pass_fill

            # Notes cell
            note_c = ws_data.cell(row=row_idx, column=col_pos + 1, value=notes_text)
            note_c.font = regular_font
            note_c.border = thin_border

        # Adjust widths for Annotated Records
        for col in ws_data.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_data.column_dimensions[col_letter].width = max(min(max_len + 3, 40), 12)

        output_stream = io.BytesIO()
        wb.save(output_stream)
        output_stream.seek(0)
        return output_stream
