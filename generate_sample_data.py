"""
generate_sample_data.py
Generates realistic college attendance datasets for testing and demonstration:
1. sample_data/attendance.xlsx (Contains known edge cases and deliberate errors)
2. sample_data/attendance_clean.xlsx (Clean dataset that passes 100% of quality gate rules)
3. sample_data/attendance.csv (CSV version for testing CSV upload)
"""

import os
import pandas as pd

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(SAMPLE_DIR, exist_ok=True)

# 1. Dataset with deliberate errors covering all MVP validation rules
messy_records = [
    # Normal valid records
    {
        "Student ID": "ENG2024-001",
        "Student Name": "Aarav Sharma",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 28,
        "Attendance %": 93.3,
        "Remarks": "Valid record - high attendance",
    },
    {
        "Student ID": "ENG2024-002",
        "Student Name": "Ananya Iyer",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 25,
        "Attendance %": 83.3,
        "Remarks": "Valid record",
    },
    # Legitimate student in a DIFFERENT class (should NOT be flagged as duplicate)
    {
        "Student ID": "ENG2024-001",
        "Student Name": "Aarav Sharma",
        "Subject": "EC204-Digital Electronics",
        "Session/Semester": "Fall 2026",
        "Classes Held": 25,
        "Classes Attended": 24,
        "Attendance %": 96.0,
        "Remarks": "Valid record - same student, different legitimate course",
    },
    # Rule 1 Error: Missing Student ID
    {
        "Student ID": None,
        "Student Name": "Rohan Verma",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 22,
        "Attendance %": 73.3,
        "Remarks": "Error: Missing Student ID",
    },
    # Rule 1 Error: Missing Subject
    {
        "Student ID": "ENG2024-004",
        "Student Name": "Pooja Hegde",
        "Subject": None,
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 26,
        "Attendance %": 86.7,
        "Remarks": "Error: Missing Subject",
    },
    # Rule 2 Duplicate Error: Duplicate of Row 2 (ENG2024-001 in CS301 Fall 2026)
    {
        "Student ID": "ENG2024-001",
        "Student Name": "Aarav Sharma",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 28,
        "Attendance %": 93.3,
        "Remarks": "Duplicate: Repeat of first record",
    },
    # Rule 3 Error: Negative Classes Attended
    {
        "Student ID": "ENG2024-005",
        "Student Name": "Kavya Patel",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": -2,
        "Attendance %": 0.0,
        "Remarks": "Error: Negative present count",
    },
    # Rule 3 Error: Negative Classes Held
    {
        "Student ID": "ENG2024-006",
        "Student Name": "Siddharth Rao",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": -10,
        "Classes Attended": 8,
        "Attendance %": 80.0,
        "Remarks": "Error: Negative classes held",
    },
    # Rule 3 Error: Classes Attended Exceeds Classes Held
    {
        "Student ID": "ENG2024-007",
        "Student Name": "Meera Nambiar",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 25,
        "Classes Attended": 28,
        "Attendance %": 112.0,
        "Remarks": "Error: Attended (28) > Held (25)",
    },
    # Rule 4 Warning: Percentage Mismatch (Attended 15 / 30 = 50.0%, but reported 85.0%)
    {
        "Student ID": "ENG2024-008",
        "Student Name": "Vikram Malhotra",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 15,
        "Attendance %": 85.0,
        "Remarks": "Warning: Reported 85% instead of expected 50%",
    },
    # Rule 4 Edge Case: Zero Classes Held (Held = 0, Attended = 0, Pct = 0.0%)
    {
        "Student ID": "ENG2024-009",
        "Student Name": "Divya Reddy",
        "Subject": "CS305-Lab Elective",
        "Session/Semester": "Fall 2026",
        "Classes Held": 0,
        "Classes Attended": 0,
        "Attendance %": 0.0,
        "Remarks": "Valid edge case: No classes conducted yet",
    },
    # Rule 4 Warning: Zero Classes Held but Non-Zero Percentage
    {
        "Student ID": "ENG2024-010",
        "Student Name": "Aditya Joshi",
        "Subject": "CS305-Lab Elective",
        "Session/Semester": "Fall 2026",
        "Classes Held": 0,
        "Classes Attended": 0,
        "Attendance %": 100.0,
        "Remarks": "Warning: 0 held but reported 100%",
    },
    # Rule 1 & 4 Warning: Blank Percentage
    {
        "Student ID": "ENG2024-011",
        "Student Name": "Sneha Nair",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 24,
        "Attendance %": None,
        "Remarks": "Warning: Blank percentage column",
    },
    # Normal valid record
    {
        "Student ID": "ENG2024-012",
        "Student Name": "Gaurav Deshmukh",
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": 27,
        "Attendance %": 90.0,
        "Remarks": "Valid record",
    },
]

df_messy = pd.DataFrame(messy_records)
messy_excel_path = os.path.join(SAMPLE_DIR, "attendance.xlsx")
messy_csv_path = os.path.join(SAMPLE_DIR, "attendance.csv")

df_messy.to_excel(messy_excel_path, index=False)
df_messy.to_csv(messy_csv_path, index=False)
print(f"Generated {messy_excel_path} and {messy_csv_path}")

# 2. 100% Clean dataset for demonstration of passing Quality Gate
clean_records = [
    {
        "Student ID": f"ENG2024-{i:03d}",
        "Student Name": name,
        "Subject": "CS301-Data Structures",
        "Session/Semester": "Fall 2026",
        "Classes Held": 30,
        "Classes Attended": attended,
        "Attendance %": round((attended / 30.0) * 100, 1),
    }
    for i, (name, attended) in enumerate(
        [
            ("Aarav Sharma", 28),
            ("Ananya Iyer", 26),
            ("Rohan Verma", 24),
            ("Pooja Hegde", 29),
            ("Kavya Patel", 27),
            ("Siddharth Rao", 25),
            ("Meera Nambiar", 30),
            ("Vikram Malhotra", 22),
            ("Divya Reddy", 27),
            ("Aditya Joshi", 23),
        ],
        start=1,
    )
]

df_clean = pd.DataFrame(clean_records)
clean_excel_path = os.path.join(SAMPLE_DIR, "attendance_clean.xlsx")
df_clean.to_excel(clean_excel_path, index=False)
print(f"Generated {clean_excel_path}")
