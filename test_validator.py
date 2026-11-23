"""
test_validator.py
Unit tests verifying all validation rules for Attendance Spreadsheet Quality Gate:
- Rule 1: Missing Values (Student ID, Subject, Held, Attended)
- Rule 2: Duplicate Records (Student + Subject; legitimate multiple classes allowed)
- Rule 3: Invalid Attendance Counts (negative attended, negative held, attended > held, non-numeric)
- Rule 4: Attendance Percentage Validation (calculation check, zero classes held handling)
- Excel Report Generation
"""

import pandas as pd
import pytest
from validator import AttendanceValidator, ValidationIssue, ValidationSummary


def test_clean_data_passes_validation():
    data = {
        "Student ID": ["STU001", "STU002", "STU003"],
        "Student Name": ["Alice Smith", "Bob Jones", "Charlie Brown"],
        "Subject": ["CS101", "CS101", "CS101"],
        "Classes Held": [20, 20, 20],
        "Classes Attended": [18, 20, 15],
        "Attendance %": [90.0, 100.0, 75.0],
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator()
    issues, summary = validator.validate(df)

    assert len(issues) == 0
    assert summary.total_records == 3
    assert summary.total_issues == 0
    assert summary.quality_gate_passed is True
    assert summary.status_label == "PASSED"


def test_missing_student_id_and_subject():
    data = {
        "Student ID": ["STU001", None, "STU003"],
        "Subject": ["CS101", "CS102", ""],
        "Classes Held": [20, 20, 20],
        "Classes Attended": [18, 15, 14],
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator()
    issues, summary = validator.validate(df)

    # Row 3 (index 1) has missing student id
    # Row 4 (index 2) has missing subject
    missing_issues = [i for i in issues if i.issue_type == "Missing Value"]
    assert len(missing_issues) == 2
    assert summary.total_errors == 2
    assert summary.quality_gate_passed is False
    assert summary.status_label == "FAILED"


def test_invalid_attendance_counts_negative_and_overflow():
    data = {
        "Student ID": ["STU001", "STU002", "STU003", "STU004"],
        "Subject": ["CS101", "CS101", "CS101", "CS101"],
        "Classes Held": [-10, 20, 15, 20],
        "Classes Attended": [5, -2, 18, "invalid"],
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator()
    issues, summary = validator.validate(df)

    # STU001: negative held (-10)
    # STU002: negative attended (-2)
    # STU003: attended 18 > held 15
    # STU004: attended non-numeric "invalid"
    count_issues = [i for i in issues if i.issue_type == "Invalid Attendance Count"]
    assert len(count_issues) == 4
    for issue in count_issues:
        assert issue.severity == "Error"


def test_duplicate_records_and_legitimate_multiple_classes():
    data = {
        "Student ID": [
            "STU001",  # Row 2: STU001 in CS101
            "STU001",  # Row 3: STU001 in CS102 (Legitimate different class, should NOT be flagged!)
            "STU001",  # Row 4: STU001 in CS101 (Duplicate of Row 2!)
            "STU002",  # Row 5: STU002 in CS101
        ],
        "Subject": ["CS101", "CS102", "CS101", "CS101"],
        "Classes Held": [20, 25, 20, 20],
        "Classes Attended": [18, 22, 18, 19],
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator()
    issues, summary = validator.validate(df)

    dup_issues = [i for i in issues if i.issue_type == "Duplicate Record"]
    assert len(dup_issues) == 1
    assert dup_issues[0].row_number == 4
    assert dup_issues[0].student_id == "STU001"
    assert "Row 2" in dup_issues[0].explanation


def test_percentage_calculation_and_mismatch():
    data = {
        "Student ID": ["STU001", "STU002", "STU003"],
        "Subject": ["CS101", "CS101", "CS101"],
        "Classes Held": [20, 20, 0],
        "Classes Attended": [15, 10, 0],
        # STU001: 15/20 = 75%, reported 75% -> OK
        # STU002: 10/20 = 50%, reported 85% -> Mismatch
        # STU003: 0/0 -> Held 0, attended 0, reported 0% -> Handled safely
        "Attendance %": [75.0, 85.0, 0.0],
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator(percentage_tolerance=0.5)
    issues, summary = validator.validate(df)

    pct_issues = [i for i in issues if i.issue_type == "Percentage Mismatch"]
    assert len(pct_issues) == 1
    assert pct_issues[0].student_id == "STU002"
    assert "85.0%" in pct_issues[0].explanation
    assert "50.0%" in pct_issues[0].explanation


def test_zero_classes_held_with_nonzero_percentage():
    data = {
        "Student ID": ["STU001"],
        "Subject": ["CS101"],
        "Classes Held": [0],
        "Classes Attended": [0],
        "Attendance %": [100.0],  # Held 0 but reports 100%
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator()
    issues, summary = validator.validate(df)

    pct_issues = [i for i in issues if i.issue_type == "Percentage Mismatch"]
    assert len(pct_issues) == 1
    assert "Classes held is 0" in pct_issues[0].explanation


def test_generate_excel_report():
    data = {
        "Student ID": ["STU001", "STU002"],
        "Subject": ["CS101", "CS101"],
        "Classes Held": [20, 20],
        "Classes Attended": [25, 15],  # 25 > 20 error
    }
    df = pd.DataFrame(data)
    validator = AttendanceValidator()
    issues, summary = validator.validate(df)
    report_bytes = AttendanceValidator.generate_excel_report(df, issues, summary, "test_file.xlsx")

    assert report_bytes is not None
    assert report_bytes.getbuffer().nbytes > 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
