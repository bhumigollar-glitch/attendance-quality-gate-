import re
from typing import List, Set
from app.rules.base import BaseRuleSet, RuleDefinition, Severity


class RuleSetV100(BaseRuleSet):
    """
    Validation Rule Set v1.0.0 (Standard Baseline).
    Implements core attendance validation rules as specified in PRD APP-059.
    """
    version: str = "v1.0.0"
    name: str = "Standard Attendance Rules v1.0.0"
    description: str = (
        "Core attendance validation baseline. Permitted statuses: Present, Absent, Leave. "
        "Strict alphanumeric student identifiers (3-20 chars). Comprehensive duplicate detection."
    )

    required_columns: List[str] = [
        "student_id",
        "student_name",
        "attendance_date",
        "attendance_status",
    ]
    optional_columns: List[str] = ["class_id"]

    permitted_statuses: Set[str] = {"present", "absent", "leave"}

    student_id_pattern = re.compile(r"^[A-Za-z0-9_-]{3,20}$")

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
            description="Unexpected extra columns were found. Under the documented ingestion policy, extra columns are permitted but flagged with a warning.",
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
            description="Attendance date must be a valid, parseable calendar date in an accepted format (e.g. YYYY-MM-DD or standard slashes).",
            severity=Severity.BLOCKING,
            category="FORMAT",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-003",
            name="Permitted Attendance Status",
            description="Attendance status must belong to the permitted set: Present, Absent, or Leave.",
            severity=Severity.BLOCKING,
            category="INTEGRITY",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-004",
            name="Valid Student Identifier",
            description="Student ID must follow the standard identifier format (3-20 characters: letters, numbers, hyphens, underscores).",
            severity=Severity.BLOCKING,
            category="FORMAT",
        ),
        RuleDefinition(
            rule_id="RULE-VAL-005",
            name="No Duplicate Attendance Records",
            description="A student cannot have more than one attendance record for the same date (and class_id if specified).",
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
