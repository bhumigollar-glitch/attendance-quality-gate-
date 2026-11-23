import re
from typing import List, Set
from app.rules.base import BaseRuleSet, RuleDefinition, Severity


class RuleSetV110(BaseRuleSet):
    """
    Validation Rule Set v1.1.0 (Extended Attendance Rules).
    Adds support for 'Late', 'Excused', and 'Half-Day' attendance statuses,
    and supports extended student identifiers up to 30 characters including dots.
    """
    version: str = "v1.1.0"
    name: str = "Extended Attendance Rules v1.1.0"
    description: str = (
        "Extended rule set supporting broader attendance statuses (Present, Absent, Leave, Late, Excused, Half-Day) "
        "and flexible student identifiers up to 30 characters."
    )

    required_columns: List[str] = [
        "student_id",
        "student_name",
        "attendance_date",
        "attendance_status",
    ]
    optional_columns: List[str] = ["class_id"]

    permitted_statuses: Set[str] = {
        "present",
        "absent",
        "leave",
        "late",
        "excused",
        "half-day",
    }

    student_id_pattern = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")

    allowed_date_formats: List[str] = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]

    rules: List[RuleDefinition] = [
        RuleDefinition(
            rule_id="RULE-SCH-001",
            name="Required Columns Present",
            description="The spreadsheet must contain all mandatory columns: student_id, student_name, attendance_date, attendance_status.",
            severity=Severity.BLOCKING,
            category="SCHEMA",
        ),
        RuleDefinition(
            rule_id="RULE-SCH-002",
            name="Documented Unexpected Columns",
            description="Unexpected extra columns were found. Flagged with a warning according to ingestion policy.",
            severity=Severity.WARNING,
            category="SCHEMA",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-001",
            name="Missing Required Value",
            description="A required field value (student_id, student_name, attendance_date, or attendance_status) is null or blank.",
            severity=Severity.BLOCKING,
            category="INTEGRITY",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-002",
            name="Valid Date Format",
            description="Attendance date must be a valid, parseable calendar date in an accepted format.",
            severity=Severity.BLOCKING,
            category="FORMAT",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-003",
            name="Permitted Attendance Status",
            description="Attendance status must belong to: Present, Absent, Leave, Late, Excused, or Half-Day.",
            severity=Severity.BLOCKING,
            category="INTEGRITY",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-004",
            name="Valid Student Identifier",
            description="Student ID must be 3-30 characters (letters, numbers, underscores, hyphens, or dots).",
            severity=Severity.BLOCKING,
            category="FORMAT",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-005",
            name="No Duplicate Attendance Records",
            description="A student cannot have duplicate attendance records for the same date and class.",
            severity=Severity.BLOCKING,
            category="INTEGRITY",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-006",
            name="Unsafe Row Data",
            description="Row contains corrupt or unsupported characters that cannot be safely cleaned automatically.",
            severity=Severity.BLOCKING,
            category="CLEANING",
        ),
    ]

    def get_rules(self) -> List[RuleDefinition]:
        return self.rules
