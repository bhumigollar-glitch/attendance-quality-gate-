# Attendance Spreadsheet Quality Gate (MVP)

A web application and deterministic data-quality gate that checks college attendance spreadsheets for common data-quality issues and generates comprehensive, downloadable audit reports.

---

## 1. Project Overview

* **Project Name:** Attendance Spreadsheet Quality Gate
* **Project Type:** Web Application / Data Quality Validation Tool
* **Objective:** Enable faculty and academic administrators to upload attendance spreadsheets, automatically validate records against deterministic data-quality rules, review detected issues on an interactive dashboard, and export formatted error reports.
* **Target Users:**
  * College faculty
  * Academic administrators
  * Staff responsible for attendance compilation and accreditation reporting

---

## 2. Problem Statement

Attendance spreadsheets collected across departments and semesters frequently contain:
* Missing student identifiers or course details
* Accidental duplicate entries for the same student in the same class session
* Impossible attendance counts (e.g., negative counts or attended > conducted)
* Calculation discrepancies in attendance percentages

Manually identifying these issues across hundreds of student records is time-consuming, prone to human oversight, and delays reporting cycles. The **Attendance Spreadsheet Quality Gate** automates basic validation without replacing the institution's existing Student Information System (SIS) or Attendance Management System (AMS).

---

## 3. MVP Features

| ID | Feature | Description | Priority |
|---|---|---|---|
| **F01** | **File Upload** | Upload Excel (`.xlsx`, `.xls`) or CSV (`.csv`) attendance files with automatic column detection. | Must have |
| **F02** | **Missing-Value Detection** | Identify missing required fields (`Student ID`, `Subject`, `Classes Held`, `Classes Attended`). | Must have |
| **F03** | **Duplicate Detection** | Identify repeated student + class session records using defined composite keys; legitimate multi-course enrollments are not flagged. | Must have |
| **F04** | **Attendance Validation** | Detect impossible attendance counts (negative attended, negative held, attended > held, non-numeric values). | Must have |
| **F05** | **Results Dashboard** | Interactive web dashboard with pass/fail decision, KPI summary metrics, category breakdowns, and filterable issues table. | Must have |
| **F06** | **Error Report Export** | Download detected issues and full annotated data as a formatted multi-sheet Excel report (`.xlsx`) or CSV. | Must have |

---

## 4. Validation Rules

### Rule 1: Missing Values
Flags records where any required field is missing, blank, `NaN`, or contains placeholder strings (`"N/A"`, `"-"`, `"NULL"`):
* **Student ID:** Cannot be blank.
* **Subject / Course:** Cannot be blank.
* **Classes Held & Attended:** Must have a recorded count.
* *Severity:* **Error**

### Rule 2: Duplicate Records
Flags repeated records sharing the same student and class-session / subject combination:
* Composite key: `[Student ID, Subject, Session/Date]`.
* **Important:** A student legitimately appearing in multiple different courses (e.g. CS101 and EC204) is **not** flagged.
* First occurrence is retained; subsequent duplicate entries are flagged with reference to the original row number.
* *Severity:* **Warning**

### Rule 3: Invalid Attendance Counts
Flags impossible attendance count values:
1. **Negative Present Count:** `Classes Attended < 0`
2. **Negative Classes Held:** `Classes Held < 0`
3. **Attendance Overflow:** `Classes Attended > Classes Held` (a student cannot attend more classes than were conducted)
4. **Non-numeric Characters:** Values such as `"absent"` or `"ten"` in numeric fields.
* *Severity:* **Error**

### Rule 4: Attendance Percentage Validation
If the spreadsheet contains an attendance percentage column:
* Expected percentage is calculated:  
  $$\text{Attendance Percentage} = \left(\frac{\text{Classes Attended}}{\text{Classes Held}}\right) \times 100$$
* Compares reported vs. calculated value using configurable tolerance (default $\pm 0.5\%$).
* **Zero Classes Held Handling:** If `Classes Held == 0` and `Classes Attended == 0`, percentage is verified as `0.0%` (or N/A) without division-by-zero errors. If non-zero percentage is reported with 0 classes held, it is flagged.
* *Severity:* **Warning**

---

## 5. Technology Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core validation logic and data processing engine |
| **Streamlit** | Interactive web interface and results dashboard |
| **Pandas** | In-memory spreadsheet parsing, filtering, and analysis |
| **OpenPyXL** | Multi-sheet styled Excel report generation with formatted headers and badges |
| **Pytest** | Automated unit test suite verifying all validation rules |
| **Git / GitHub** | Version control and collaborative development |

---

## 6. Project Structure

```text
attendance-quality-gate/
│
├── app.py                     # Streamlit web application (UI, upload, results, export)
├── validator.py               # Core validation rules engine and Excel report generator
├── test_validator.py          # Pytest unit tests for all validation rules
├── generate_sample_data.py    # Script generating synthetic test datasets
├── requirements.txt           # Python package dependencies
├── README.md                  # Project documentation and user guide
└── sample_data/
    ├── attendance.xlsx        # Synthetic dataset with deliberate errors & edge cases
    ├── attendance_clean.xlsx  # 100% clean dataset demonstrating passing quality gate
    └── attendance.csv         # CSV version for file format testing
```

---

## 7. Installation & Quickstart

### Prerequisites
* Python 3.10 or higher
* `pip` package manager

### 1. Clone or Navigate to the Repository
```bash
cd attendance-quality-gate
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
The application will launch automatically in your default browser at `http://localhost:8501`.

### 5. Run the Automated Test Suite
```bash
pytest test_validator.py -v
```

---

## 8. User Workflow

1. **Open the Application:** Access the dashboard in your browser.
2. **Upload or Quick-Test:**
   * Drag and drop any `.xlsx`, `.xls`, or `.csv` attendance spreadsheet.
   * Or click **"⚠️ Test Errors"** / **"✅ Test Clean"** in the sidebar to test immediately with built-in synthetic datasets.
3. **Verify Column Mapping:** The system auto-detects column names (`Student ID`, `Subject`, `Classes Held`, etc.). You can adjust mappings in the expandable section if needed.
4. **View Validation Summary:**
   * **Overall Gate Decision:** `PASSED` (green), `PASSED WITH WARNINGS` (yellow), or `FAILED` (red).
   * **Metrics:** Total records, total issues, count of Errors (must fix) and Warnings.
   * **Visual Charts:** Breakdown by issue type and severity.
5. **Review Detected Issues:**
   * Explore the results table with **Row Number**, **Student ID**, **Issue Type**, **Severity**, **Explanation**, and **Suggested Action**.
   * Use real-time filters by severity, issue category, or search keywords.
6. **Download Error Report:** Click **"📥 Download Excel Report"** to export an audit workbook.

---

## 9. Generated Excel Report Structure

The downloaded `.xlsx` report contains three dedicated worksheets:

1. **Quality Gate Summary:**
   * File metadata, validation timestamp, overall gate pass/fail status.
   * High-level metrics (total records, error count, warning count).
   * Issue category breakdown table.

2. **Detected Issues:**
   * Tabular list of all detected anomalies.
   * Exact spreadsheet row numbers (Excel 1-indexed).
   * Color-coded severity badges (Red for Error, Yellow for Warning).
   * Actionable remediation instructions.

3. **Annotated Records:**
   * Full copy of the original uploaded spreadsheet.
   * Appended `Gate Status` (`Valid` / `Has Issues`) and `Detected Notes` columns for row-by-row reconciliation.

---

## 10. Features Excluded from the MVP

As defined in the specification, the initial MVP does not include:
* QR-code attendance marking
* Facial recognition / biometric scanning
* Student and faculty user login / authentication
* Automated attendance corrections
* AI-based anomaly detection
* Email or SMS notifications
* Full-scale Student Information System (SIS)

---

## 11. Future Roadmap

1. **Cross-file Reconciliation:** Validate student IDs against an official college enrollment master register.
2. **Configurable Rule Thresholds:** Custom attendance thresholds (e.g., flagging students below 75% mandatory attendance).
3. **Validation Audit History:** Storing historical validation runs in a database.
4. **Interactive Correction Mode:** Allowing operators to fix errors in-browser and download a corrected spreadsheet.
