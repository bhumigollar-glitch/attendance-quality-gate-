import json
from pathlib import Path
import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parent

# 1. valid_clean.csv
valid_clean = [
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "STU002", "student_name": "Bob Smith", "attendance_date": "2024-10-01", "attendance_status": "Absent", "class_id": "CS101"},
    {"student_id": "STU003", "student_name": "Carol Williams", "attendance_date": "2024-10-01", "attendance_status": "Leave", "class_id": "CS101"},
    {"student_id": "STU004", "student_name": "David Brown", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS102"},
]

# 2. valid_with_whitespace.csv (Needs conservative cleaning)
valid_whitespace = [
    {"student_id": "  STU001  ", "student_name": "  Alice Johnson  ", "attendance_date": " 2024-10-01 ", "attendance_status": " present ", "class_id": " CS101 "},
    {"student_id": "STU002 ", "student_name": "Bob Smith ", "attendance_date": "01/10/2024", "attendance_status": "absent", "class_id": "CS101"},
    {"student_id": " STU003", "student_name": " Carol Williams", "attendance_date": "2024/10/01", "attendance_status": " leave ", "class_id": "CS101"},
]

# 3. valid_v1_1_extended.csv (Late / Excused / dot in student ID)
valid_v1_1 = [
    {"student_id": "STU.001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Late", "class_id": "CS101"},
    {"student_id": "STU.002", "student_name": "Bob Smith", "attendance_date": "2024-10-01", "attendance_status": "Excused", "class_id": "CS101"},
    {"student_id": "STU.003", "student_name": "Carol Williams", "attendance_date": "2024-10-01", "attendance_status": "Half-Day", "class_id": "CS101"},
]

# 4. invalid_missing_columns.csv
invalid_missing_cols = [
    {"student_id": "STU001", "student_name": "Alice Johnson"},
    {"student_id": "STU002", "student_name": "Bob Smith"},
]

# 5. invalid_missing_values.csv
invalid_missing_vals = [
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "", "student_name": "Bob Smith", "attendance_date": "2024-10-01", "attendance_status": "Absent", "class_id": "CS101"},
    {"student_id": "STU003", "student_name": "", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "STU004", "student_name": "David Brown", "attendance_date": "", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "STU005", "student_name": "Eve Davis", "attendance_date": "2024-10-01", "attendance_status": "", "class_id": "CS101"},
]

# 6. invalid_duplicate_records.csv
invalid_duplicates = [
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "STU002", "student_name": "Bob Smith", "attendance_date": "2024-10-01", "attendance_status": "Absent", "class_id": "CS101"},
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Absent", "class_id": "CS101"},  # Duplicate
]

# 7. invalid_date_formats.csv
invalid_dates = [
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "STU002", "student_name": "Bob Smith", "attendance_date": "tomorrow", "attendance_status": "Absent", "class_id": "CS101"},
    {"student_id": "STU003", "student_name": "Carol Williams", "attendance_date": "99/99/2024", "attendance_status": "Leave", "class_id": "CS101"},
]

# 8. invalid_statuses.csv
invalid_statuses = [
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Holiday", "class_id": "CS101"},
    {"student_id": "STU002", "student_name": "Bob Smith", "attendance_date": "2024-10-01", "attendance_status": "Skipped", "class_id": "CS101"},
    {"student_id": "STU003", "student_name": "Carol Williams", "attendance_date": "2024-10-01", "attendance_status": "Unknown", "class_id": "CS101"},
]

# 9. invalid_student_ids.csv
invalid_student_ids = [
    {"student_id": "STU#123", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101"},
    {"student_id": "??", "student_name": "Bob Smith", "attendance_date": "2024-10-01", "attendance_status": "Absent", "class_id": "CS101"},
    {"student_id": "A" * 50, "student_name": "Carol Williams", "attendance_date": "2024-10-01", "attendance_status": "Leave", "class_id": "CS101"},
]

# 10. mixed_messy_fixture.csv (Contains unexpected extra column 'remarks', bad date, bad status, and duplicate)
mixed_messy = [
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101", "remarks": "On time"},
    {"student_id": "STU002", "student_name": "Bob Smith", "attendance_date": "not-a-date", "attendance_status": "Absent", "class_id": "CS101", "remarks": "Sick"},
    {"student_id": "STU003", "student_name": "Carol Williams", "attendance_date": "2024-10-01", "attendance_status": "Vacation", "class_id": "CS101", "remarks": "Travel"},
    {"student_id": "STU001", "student_name": "Alice Johnson", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101", "remarks": "Duplicate entry"},
    {"student_id": "STU005", "student_name": "", "attendance_date": "2024-10-01", "attendance_status": "Present", "class_id": "CS101", "remarks": "Missing name"},
]

def save_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(FIXTURES_DIR / filename, index=False)

def main():
    save_csv(valid_clean, "valid_clean.csv")
    pd.DataFrame(valid_clean).to_excel(FIXTURES_DIR / "valid_clean.xlsx", index=False)

    save_csv(valid_whitespace, "valid_with_whitespace.csv")
    save_csv(valid_v1_1, "valid_v1_1_extended.csv")
    save_csv(invalid_missing_cols, "invalid_missing_columns.csv")
    save_csv(invalid_missing_vals, "invalid_missing_values.csv")
    save_csv(invalid_duplicates, "invalid_duplicate_records.csv")
    save_csv(invalid_dates, "invalid_date_formats.csv")
    save_csv(invalid_statuses, "invalid_statuses.csv")
    save_csv(invalid_student_ids, "invalid_student_ids.csv")
    save_csv(mixed_messy, "mixed_messy_fixture.csv")

    manifest = {
        "description": "Quality Gate Fixture Pack for Testing and Demonstration",
        "fixtures": [
            {
                "file": "valid_clean.csv",
                "format": "csv",
                "expected_decision": "ACCEPTED",
                "expected_errors": 0,
                "expected_warnings": 0,
                "description": "Standard clean attendance CSV file with all required fields."
            },
            {
                "file": "valid_clean.xlsx",
                "format": "xlsx",
                "expected_decision": "ACCEPTED",
                "expected_errors": 0,
                "expected_warnings": 0,
                "description": "Standard clean attendance Excel spreadsheet."
            },
            {
                "file": "valid_with_whitespace.csv",
                "format": "csv",
                "expected_decision": "ACCEPTED",
                "expected_errors": 0,
                "expected_warnings": 0,
                "description": "Attendance data with leading/trailing whitespaces and mixed casing to verify conservative normalization."
            },
            {
                "file": "valid_v1_1_extended.csv",
                "format": "csv",
                "expected_decision_v1_0": "QUARANTINED",
                "expected_decision_v1_1": "ACCEPTED",
                "description": "Tests rule set versioning: fails v1.0.0 due to 'Late' status and dot in student ID, succeeds under v1.1.0."
            },
            {
                "file": "invalid_missing_columns.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 1,
                "expected_rule": "RULE-SCH-001",
                "description": "Missing required columns (attendance_date, attendance_status)."
            },
            {
                "file": "invalid_missing_values.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 4,
                "expected_rule": "RULE-VAL-001",
                "description": "Rows with missing student_id, student_name, attendance_date, and attendance_status."
            },
            {
                "file": "invalid_duplicate_records.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 1,
                "expected_rule": "RULE-VAL-005",
                "description": "Duplicate attendance record for student STU001 on the same date and class."
            },
            {
                "file": "invalid_date_formats.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 2,
                "expected_rule": "RULE-VAL-002",
                "description": "Unparseable and invalid dates ('tomorrow', '99/99/2024')."
            },
            {
                "file": "invalid_statuses.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 3,
                "expected_rule": "RULE-VAL-003",
                "description": "Statuses not in permitted set ('Holiday', 'Skipped', 'Unknown')."
            },
            {
                "file": "invalid_student_ids.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 3,
                "expected_rule": "RULE-VAL-004",
                "description": "Student IDs violating character format constraints."
            },
            {
                "file": "mixed_messy_fixture.csv",
                "format": "csv",
                "expected_decision": "QUARANTINED",
                "expected_errors": 4,
                "expected_warnings": 1,
                "description": "Messy fixture with extra column ('remarks'), duplicate record, bad date, bad status, and missing name."
            }
        ]
    }

    with open(FIXTURES_DIR / "fixtures_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("Successfully generated all fixtures and manifest!")

if __name__ == "__main__":
    main()
