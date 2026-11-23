import datetime
import re
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from app.rules.base import BaseRuleSet, ValidationIssue, Severity


class ValidationResult:
    """Encapsulates the complete result of a dataset validation run."""
    def __init__(
        self,
        issues: List[ValidationIssue],
        total_rows: int,
        valid_rows: int,
        invalid_rows: int,
        error_count: int,
        warning_count: int,
        decision: str,
        rule_version: str,
    ):
        self.issues = issues
        self.total_rows = total_rows
        self.valid_rows = valid_rows
        self.invalid_rows = invalid_rows
        self.error_count = error_count
        self.warning_count = warning_count
        self.decision = decision
        self.rule_version = rule_version


class ValidatorService:
    """Executes deterministic schema and row-level quality checks against a versioned rule set."""

    @classmethod
    def validate(cls, df: pd.DataFrame, rule_set: BaseRuleSet) -> ValidationResult:
        issues: List[ValidationIssue] = []

        # 1. Schema Validation
        columns_present = [str(col).strip() for col in df.columns]
        missing_columns = [
            req_col for req_col in rule_set.required_columns
            if req_col not in columns_present
        ]

        if missing_columns:
            rule_def = rule_set.get_rule_by_id("RULE-SCH-001")
            issues.append(
                ValidationIssue(
                    row_number=None,
                    column_name=", ".join(missing_columns),
                    invalid_value=None,
                    rule_id="RULE-SCH-001",
                    rule_description=rule_def.description if rule_def else "Missing required columns.",
                    severity=Severity.BLOCKING,
                    message=f"Missing required column(s): {', '.join(missing_columns)}.",
                )
            )

        # Check unexpected columns
        allowed_columns = set(rule_set.required_columns + rule_set.optional_columns)
        unexpected_columns = [col for col in columns_present if col not in allowed_columns]
        if unexpected_columns:
            rule_def = rule_set.get_rule_by_id("RULE-SCH-002")
            issues.append(
                ValidationIssue(
                    row_number=None,
                    column_name=", ".join(unexpected_columns),
                    invalid_value=None,
                    rule_id="RULE-SCH-002",
                    rule_description=rule_def.description if rule_def else "Unexpected columns found.",
                    severity=Severity.WARNING,
                    message=f"Documented policy: Extra column(s) detected: {', '.join(unexpected_columns)}. Allowed to proceed with warning.",
                )
            )

        # If missing required columns, we cannot perform reliable row validation
        total_rows = len(df)
        if missing_columns:
            return ValidationResult(
                issues=issues,
                total_rows=total_rows,
                valid_rows=0,
                invalid_rows=total_rows,
                error_count=1,
                warning_count=1 if unexpected_columns else 0,
                decision="QUARANTINED",
                rule_version=rule_set.version,
            )

        # 2. Row-Level Data Quality Rules
        # We track duplicate records using a composite key: (student_id, date, class_id)
        seen_keys: Dict[Tuple[str, str, str], int] = {}
        rows_with_blocking_errors = set()

        for idx, row in df.iterrows():
            # Physical spreadsheet row: header is row 1, data starts at row 2
            row_num = idx + 2
            row_has_blocking_error = False

            # Extract raw values
            raw_student_id = str(row.get("student_id", "")).strip()
            raw_student_name = str(row.get("student_name", "")).strip()
            raw_date = str(row.get("attendance_date", "")).strip()
            raw_status = str(row.get("attendance_status", "")).strip()
            raw_class_id = str(row.get("class_id", "")).strip() if "class_id" in row else ""

            # Check 1: Missing Required Values (RULE-VAL-001)
            for field_name, field_val in [
                ("student_id", raw_student_id),
                ("student_name", raw_student_name),
                ("attendance_date", raw_date),
                ("attendance_status", raw_status),
            ]:
                if not field_val or field_val.lower() in ("nan", "none", "null"):
                    rule_def = rule_set.get_rule_by_id("RULE-VAL-001")
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            column_name=field_name,
                            invalid_value=field_val if field_val else "<EMPTY>",
                            rule_id="RULE-VAL-001",
                            rule_description=rule_def.description if rule_def else "Missing required value.",
                            severity=Severity.BLOCKING,
                            message=f"Column '{field_name}' must not be empty or null.",
                        )
                    )
                    row_has_blocking_error = True

            # Check 2: Student ID Format (RULE-VAL-004)
            if raw_student_id and raw_student_id.lower() not in ("nan", "none", "null"):
                if not rule_set.student_id_pattern.match(raw_student_id):
                    rule_def = rule_set.get_rule_by_id("RULE-VAL-004")
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            column_name="student_id",
                            invalid_value=raw_student_id,
                            rule_id="RULE-VAL-004",
                            rule_description=rule_def.description if rule_def else "Invalid student identifier.",
                            severity=Severity.BLOCKING,
                            message=f"Student ID '{raw_student_id}' does not match the required pattern ({rule_set.student_id_pattern.pattern}).",
                        )
                    )
                    row_has_blocking_error = True

            # Check 3: Date Parsing & Validity (RULE-VAL-002)
            parsed_date_iso: Optional[str] = None
            if raw_date and raw_date.lower() not in ("nan", "none", "null"):
                parsed_date_iso = cls._parse_date(raw_date, rule_set)
                if not parsed_date_iso:
                    rule_def = rule_set.get_rule_by_id("RULE-VAL-002")
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            column_name="attendance_date",
                            invalid_value=raw_date,
                            rule_id="RULE-VAL-002",
                            rule_description=rule_def.description if rule_def else "Invalid date format.",
                            severity=Severity.BLOCKING,
                            message=f"Date '{raw_date}' is invalid or cannot be parsed into an accepted calendar format.",
                        )
                    )
                    row_has_blocking_error = True

            # Check 4: Attendance Status Permitted Set (RULE-VAL-003)
            if raw_status and raw_status.lower() not in ("nan", "none", "null"):
                clean_status = raw_status.lower()
                if clean_status not in rule_set.permitted_statuses:
                    rule_def = rule_set.get_rule_by_id("RULE-VAL-003")
                    allowed_str = ", ".join(sorted([s.title() for s in rule_set.permitted_statuses]))
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            column_name="attendance_status",
                            invalid_value=raw_status,
                            rule_id="RULE-VAL-003",
                            rule_description=rule_def.description if rule_def else "Unsupported attendance status.",
                            severity=Severity.BLOCKING,
                            message=f"Status '{raw_status}' is invalid. Permitted values: {allowed_str}.",
                        )
                    )
                    row_has_blocking_error = True

            # Check 5: Duplicate Attendance Record (RULE-VAL-005)
            # Duplicate key: (student_id, date, class_id)
            if raw_student_id and parsed_date_iso:
                dup_key = (raw_student_id.upper(), parsed_date_iso, raw_class_id.upper())
                if dup_key in seen_keys:
                    first_row = seen_keys[dup_key]
                    rule_def = rule_set.get_rule_by_id("RULE-VAL-005")
                    class_info = f" (class_id: '{raw_class_id}')" if raw_class_id else ""
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            column_name="student_id, attendance_date",
                            invalid_value=f"{raw_student_id} on {parsed_date_iso}",
                            rule_id="RULE-VAL-005",
                            rule_description=rule_def.description if rule_def else "Duplicate attendance record.",
                            severity=Severity.BLOCKING,
                            message=f"Duplicate attendance entry for student '{raw_student_id}' on date '{parsed_date_iso}'{class_info}. Prior entry at row {first_row}.",
                        )
                    )
                    row_has_blocking_error = True
                else:
                    seen_keys[dup_key] = row_num

            # Check 6: Unsafe Row Data (RULE-VAL-006)
            for col_name, cell_val in [(c, str(row[c])) for c in df.columns]:
                if "\x00" in cell_val:  # Null byte or dangerous control characters
                    rule_def = rule_set.get_rule_by_id("RULE-VAL-006")
                    issues.append(
                        ValidationIssue(
                            row_number=row_num,
                            column_name=col_name,
                            invalid_value="<BINARY_NULL_BYTE>",
                            rule_id="RULE-VAL-006",
                            rule_description=rule_def.description if rule_def else "Unsafe row data.",
                            severity=Severity.BLOCKING,
                            message=f"Row contains unsafe binary null bytes in column '{col_name}'.",
                        )
                    )
                    row_has_blocking_error = True

            if row_has_blocking_error:
                rows_with_blocking_errors.add(row_num)

        # Calculate final metrics
        error_count = sum(1 for issue in issues if issue.severity in (Severity.BLOCKING, Severity.BLOCKING.value))
        warning_count = sum(1 for issue in issues if issue.severity in (Severity.WARNING, Severity.WARNING.value))
        invalid_rows = len(rows_with_blocking_errors)
        valid_rows = total_rows - invalid_rows

        decision = "ACCEPTED" if error_count == 0 else "QUARANTINED"

        return ValidationResult(
            issues=issues,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            error_count=error_count,
            warning_count=warning_count,
            decision=decision,
            rule_version=rule_set.version,
        )

    @staticmethod
    def _parse_date(date_str: str, rule_set: BaseRuleSet) -> Optional[str]:
        """Try parsing date using rule set formats, returning ISO YYYY-MM-DD or None."""
        clean = date_str.strip()
        for fmt in rule_set.allowed_date_formats:
            try:
                dt = datetime.datetime.strptime(clean, fmt)
                # Ensure year is within plausible range (e.g. 2000 - 2100)
                if 1900 <= dt.year <= 2100:
                    return dt.strftime("%Y-%m-%d")
            except (ValueError, OverflowError):
                continue
        return None
