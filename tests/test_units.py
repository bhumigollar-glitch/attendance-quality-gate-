import pandas as pd
import pytest
from app.rules.base import Severity
from app.rules.registry import rule_registry
from app.rules.versions.v1_0_0 import RuleSetV100
from app.rules.versions.v1_1_0 import RuleSetV110
from app.services.cleaner_service import CleanerService
from app.services.validator_service import ValidatorService


def test_rule_registry_contains_versions():
    """Verify registry has standard v1.0.0 and extended v1.1.0."""
    versions = rule_registry.list_versions()
    assert "v1.0.0" in versions
    assert "v1.1.0" in versions

    v100 = rule_registry.get("v1.0.0")
    assert isinstance(v100, RuleSetV100)
    assert len(v100.get_rules()) > 0

    assert rule_registry.get("non_existent") is None


def test_schema_validation_missing_columns():
    """Verify missing required columns produce RULE-SCH-001 blocking error."""
    df = pd.DataFrame([{"student_id": "STU1", "student_name": "Alice"}])
    rule_set = RuleSetV100()

    result = ValidatorService.validate(df, rule_set)
    assert result.decision == "QUARANTINED"
    assert result.error_count == 1
    assert any(i.rule_id == "RULE-SCH-001" and i.severity == Severity.BLOCKING for i in result.issues)


def test_schema_validation_unexpected_column_warning():
    """Verify unexpected extra column produces RULE-SCH-002 warning but accepts if data is valid."""
    df = pd.DataFrame([
        {
            "student_id": "STU001",
            "student_name": "Alice",
            "attendance_date": "2024-10-01",
            "attendance_status": "Present",
            "custom_metadata": "Extra data",
        }
    ])
    rule_set = RuleSetV100()

    result = ValidatorService.validate(df, rule_set)
    assert result.decision == "ACCEPTED"
    assert result.warning_count == 1
    assert any(i.rule_id == "RULE-SCH-002" and i.severity == Severity.WARNING for i in result.issues)


def test_missing_values_detection():
    """Verify blank / null required values are flagged with RULE-VAL-001."""
    df = pd.DataFrame([
        {"student_id": "", "student_name": "Alice", "attendance_date": "2024-10-01", "attendance_status": "Present"},
        {"student_id": "STU002", "student_name": "", "attendance_date": "2024-10-01", "attendance_status": "Present"},
        {"student_id": "STU003", "student_name": "Carol", "attendance_date": "", "attendance_status": "Present"},
        {"student_id": "STU004", "student_name": "Dave", "attendance_date": "2024-10-01", "attendance_status": ""},
    ])
    rule_set = RuleSetV100()

    result = ValidatorService.validate(df, rule_set)
    assert result.decision == "QUARANTINED"
    assert result.error_count == 4
    val_issues = [i for i in result.issues if i.rule_id == "RULE-VAL-001"]
    assert len(val_issues) == 4


def test_date_parsing_and_status_validation():
    """Verify invalid date and invalid status are flagged appropriately."""
    df = pd.DataFrame([
        {"student_id": "STU001", "student_name": "Alice", "attendance_date": "invalid-date", "attendance_status": "Present"},
        {"student_id": "STU002", "student_name": "Bob", "attendance_date": "2024-10-01", "attendance_status": "SickHoliday"},
    ])
    rule_set = RuleSetV100()

    result = ValidatorService.validate(df, rule_set)
    assert result.decision == "QUARANTINED"
    assert any(i.rule_id == "RULE-VAL-002" for i in result.issues)
    assert any(i.rule_id == "RULE-VAL-003" for i in result.issues)


def test_duplicate_attendance_detection():
    """Verify duplicate attendance records for the same student on the same date/class trigger RULE-VAL-005."""
    df = pd.DataFrame([
        {"student_id": "STU001", "student_name": "Alice", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS1"},
        {"student_id": "STU001", "student_name": "Alice", "attendance_date": "2024-10-01", "attendance_status": "Absent", "class_id": "CS1"},
    ])
    rule_set = RuleSetV100()

    result = ValidatorService.validate(df, rule_set)
    assert result.decision == "QUARANTINED"
    assert any(i.rule_id == "RULE-VAL-005" for i in result.issues)
    dup_issue = next(i for i in result.issues if i.rule_id == "RULE-VAL-005")
    assert dup_issue.row_number == 3  # Second record is row 3 in spreadsheet (row 1 is header)


def test_cleaner_service_conservative_cleaning():
    """Verify whitespace trimming, date normalization, and status casing normalization."""
    df = pd.DataFrame([
        {
            "student_id": "  STU001  ",
            "student_name": " Alice Smith  ",
            "attendance_date": " 01/10/2024 ",
            "attendance_status": " present ",
            "class_id": " MATH101 ",
        }
    ])
    rule_set = RuleSetV100()

    cleaned = CleanerService.clean(df, rule_set)
    assert cleaned.iloc[0]["student_id"] == "STU001"
    assert cleaned.iloc[0]["student_name"] == "Alice Smith"
    assert cleaned.iloc[0]["attendance_date"] == "2024-10-01"
    assert cleaned.iloc[0]["attendance_status"] == "Present"
    assert cleaned.iloc[0]["class_id"] == "MATH101"


def test_rule_versioning_differences():
    """Verify v1.1.0 allows 'Late' and extended student IDs with dots while v1.0.0 quaratines."""
    df = pd.DataFrame([
        {
            "student_id": "STU.001",
            "student_name": "Alice",
            "attendance_date": "2024-10-01",
            "attendance_status": "Late",
        }
    ])

    v100 = RuleSetV100()
    v110 = RuleSetV110()

    res_v100 = ValidatorService.validate(df, v100)
    assert res_v100.decision == "QUARANTINED"  # 'Late' not in v1.0.0 and dot not in student_id

    res_v110 = ValidatorService.validate(df, v110)
    assert res_v110.decision == "ACCEPTED"  # Valid in v1.1.0
