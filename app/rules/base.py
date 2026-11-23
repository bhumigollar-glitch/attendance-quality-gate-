from enum import Enum
from typing import List, Optional, Set, Dict, Any, Pattern
from pydantic import BaseModel, ConfigDict


class Severity(str, Enum):
    BLOCKING = "BLOCKING"  # Causes file quarantine
    WARNING = "WARNING"    # Recorded in report, does not block acceptance
    INFO = "INFO"          # Informational


class ValidationIssue(BaseModel):
    """Represents a discrete validation failure or warning detected during processing."""
    row_number: Optional[int] = None  # 1-indexed row number in spreadsheet (None for file-wide/schema issues)
    column_name: Optional[str] = None
    invalid_value: Optional[str] = None
    rule_id: str
    rule_description: str
    severity: Severity
    message: str

    model_config = ConfigDict(use_enum_values=True)


class RuleDefinition(BaseModel):
    """Metadata describing a single validation rule."""
    rule_id: str
    name: str
    description: str
    severity: Severity
    category: str  # SCHEMA, FORMAT, INTEGRITY, CLEANING

    model_config = ConfigDict(use_enum_values=True)


class BaseRuleSet:
    """Base class defining the contract for versioned attendance validation rule sets."""
    version: str
    name: str
    description: str
    required_columns: List[str] = ["student_id", "student_name", "attendance_date", "attendance_status"]
    optional_columns: List[str] = ["class_id"]
    permitted_statuses: Set[str]
    student_id_pattern: Pattern
    allowed_date_formats: List[str]

    def get_rules(self) -> List[RuleDefinition]:
        raise NotImplementedError

    def get_rule_by_id(self, rule_id: str) -> Optional[RuleDefinition]:
        for r in self.get_rules():
            if r.rule_id == rule_id:
                return r
        return None
