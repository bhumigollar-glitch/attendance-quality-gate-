"""
app.py
======
Attendance Spreadsheet Quality Gate - Web Application (MVP)

A Streamlit web application that checks attendance spreadsheets for common
data-quality issues and generates a comprehensive downloadable report.

Features:
- F01: File Upload (.xlsx, .xls, .csv) with auto-column mapping
- F02: Missing-Value Detection (Student ID, Subject, Held, Attended)
- F03: Duplicate Detection (Repeated student + class-session combination)
- F04: Attendance Validation (Negative present, negative held, present > held)
- F05: Results Dashboard (Summary KPIs, breakdown charts, filterable results table)
- F06: Error Report Export (Multi-sheet styled Excel report with OpenPyXL)
"""

import io
import os
import pandas as pd
import streamlit as st

from validator import (
    AttendanceValidator,
    DEFAULT_COLUMN_ALIASES,
    ValidationIssue,
    ValidationSummary,
)

# Page configuration
st.set_page_config(
    page_title="Attendance Quality Gate",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .status-badge-pass {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-warn {
        background-color: #FEF08A;
        color: #854D0E;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-fail {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_file(uploaded_file) -> pd.DataFrame:
    """Reads uploaded file (CSV or Excel) into a pandas DataFrame."""
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith((".xlsx", ".xls")):
            # If Excel has multiple sheets, default to first or let user choose
            xl = pd.ExcelFile(uploaded_file)
            if len(xl.sheet_names) > 1:
                st.sidebar.info(f"Sheets found: {', '.join(xl.sheet_names)}. Reading '{xl.sheet_names[0]}'.")
            df = xl.parse(xl.sheet_names[0])
        else:
            st.error("Unsupported file format. Please upload an Excel (.xlsx, .xls) or CSV (.csv) file.")
            return None
        return df
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None


def main():
    # Header Banner
    st.markdown('<div class="main-header">🛡️ Attendance Spreadsheet Quality Gate</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Automated data-quality validation and compliance gate for college attendance records.</div>',
        unsafe_allow_html=True,
    )

    # Sidebar: File Upload & Configuration
    with st.sidebar:
        st.header("📁 Spreadsheet Upload")
        uploaded_file = st.file_uploader(
            "Upload an attendance spreadsheet",
            type=["xlsx", "xls", "csv"],
            help="Upload college attendance records in Excel or CSV format.",
        )

        # Quick-load sample data buttons
        st.markdown("---")
        st.subheader("🧪 Quick-Test Sample Data")
        col_s1, col_s2 = st.columns(2)
        sample_path_messy = os.path.join(os.path.dirname(__file__), "sample_data", "attendance.xlsx")
        sample_path_clean = os.path.join(os.path.dirname(__file__), "sample_data", "attendance_clean.xlsx")

        load_sample = False
        sample_type = None
        if col_s1.button("⚠️ Test Errors", use_container_width=True, help="Load synthetic attendance with deliberate edge cases."):
            load_sample = True
            sample_type = "messy"
        if col_s2.button("✅ Test Clean", use_container_width=True, help="Load 100% clean attendance data."):
            load_sample = True
            sample_type = "clean"

        # Validation Options
        st.markdown("---")
        st.subheader("⚙️ Validation Rules Config")
        pct_tolerance = st.slider(
            "Percentage Tolerance (±%)",
            min_value=0.0,
            max_value=2.0,
            value=0.5,
            step=0.1,
            help="Allowable rounding difference between reported and calculated attendance percentage.",
        )

        st.markdown("---")
        st.markdown(
            """
            **Validation Rules Enforced:**
            - **Rule 1:** Missing Values (Student ID, Subject, Counts)
            - **Rule 2:** Duplicate Records (Student + Class Session)
            - **Rule 3:** Invalid Counts (Negative, Attended > Held)
            - **Rule 4:** Attendance % Verification
            """
        )

    # Determine input data source
    df_raw = None
    file_display_name = ""

    if uploaded_file is not None:
        df_raw = load_file(uploaded_file)
        file_display_name = uploaded_file.name
    elif load_sample or "sample_loaded" in st.session_state:
        if load_sample:
            st.session_state["sample_loaded"] = sample_type
        current_sample = st.session_state.get("sample_loaded", "messy")
        target_path = sample_path_clean if current_sample == "clean" else sample_path_messy
        if os.path.exists(target_path):
            df_raw = pd.read_excel(target_path)
            file_display_name = os.path.basename(target_path)
            st.sidebar.success(f"Loaded: `{file_display_name}`")
        else:
            st.warning("Sample data file not found. Please upload a spreadsheet.")

    if df_raw is None:
        # Welcome / Empty State Guide
        st.info("👆 Please upload an attendance spreadsheet (`.xlsx` or `.csv`) using the sidebar, or click a **Quick-Test** button.")
        
        st.markdown("### How the Quality Gate Works")
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            st.markdown(
                """
                #### 1. Upload & Map
                Upload your attendance sheet. Columns are automatically mapped:
                - Student ID / Roll No / USN
                - Subject / Course Code
                - Classes Held & Attended
                - Attendance Percentage
                """
            )
        with col_w2:
            st.markdown(
                """
                #### 2. Deterministic Quality Audit
                The gate examines every row:
                - Detects missing IDs or subject names
                - Flags impossible counts (e.g. Present > Held)
                - Detects double submissions for same class
                - Validates attendance calculations
                """
            )
        with col_w3:
            st.markdown(
                """
                #### 3. Review & Export
                - Immediate pass/fail gate decision
                - Filterable table with suggested actions
                - Download multi-sheet Excel report with full audit trail
                """
            )

        # Show rule reference table
        st.markdown("---")
        st.markdown("#### Quality Gate Rule Matrix")
        rule_data = [
            {"Rule": "Rule 1: Missing Values", "Description": "Identifies missing required Student ID, Subject, Classes Held, or Classes Attended.", "Severity": "Error", "Standard": "Must Have"},
            {"Rule": "Rule 2: Duplicate Records", "Description": "Detects repeated entries for the same student and class session. Legitimate multi-course entries are preserved.", "Severity": "Warning", "Standard": "Must Have"},
            {"Rule": "Rule 3: Invalid Attendance Counts", "Description": "Flags negative present count, negative classes held, non-numeric values, or Present > Held.", "Severity": "Error", "Standard": "Must Have"},
            {"Rule": "Rule 4: Percentage Verification", "Description": "Compares reported percentage against (Attended / Held) * 100. Handles 0 classes held gracefully.", "Severity": "Warning", "Standard": "Must Have"},
        ]
        st.table(pd.DataFrame(rule_data))
        return

    # Column Mapping Expander
    with st.expander("🔍 Verified Column Mapping (Auto-Detected)", expanded=False):
        detected_mapping = AttendanceValidator.detect_columns(df_raw)
        col_m1, col_m2 = st.columns(2)
        
        custom_mapping = {}
        all_cols = ["-- Not Present --"] + list(df_raw.columns)

        with col_m1:
            for field in ["student_id", "subject", "classes_held"]:
                default_val = detected_mapping.get(field)
                idx = all_cols.index(default_val) if default_val in all_cols else 0
                custom_mapping[field] = st.selectbox(
                    f"Column for '{field.replace('_', ' ').title()}'",
                    options=all_cols,
                    index=idx,
                    key=f"col_map_{field}",
                )
                if custom_mapping[field] == "-- Not Present --":
                    custom_mapping[field] = None

        with col_m2:
            for field in ["classes_attended", "attendance_percentage", "session_date"]:
                default_val = detected_mapping.get(field)
                idx = all_cols.index(default_val) if default_val in all_cols else 0
                custom_mapping[field] = st.selectbox(
                    f"Column for '{field.replace('_', ' ').title()}'",
                    options=all_cols,
                    index=idx,
                    key=f"col_map_{field}",
                )
                if custom_mapping[field] == "-- Not Present --":
                    custom_mapping[field] = None

    # Run Validation
    validator = AttendanceValidator(
        percentage_tolerance=pct_tolerance,
    )
    issues, summary = validator.validate(df_raw, custom_mapping=custom_mapping)

    # Section: Gate Summary & KPIs
    st.markdown("### 📊 Validation Results & Quality Gate Status")
    
    # Status Banner
    col_status, col_dl = st.columns([3, 1])
    with col_status:
        if summary.status_label == "PASSED":
            st.markdown(
                f'<div class="status-badge-pass" style="font-size:1.15rem; margin-bottom:12px;">✅ QUALITY GATE PASSED: File is clean and ready for reporting</div>',
                unsafe_allow_html=True,
            )
        elif summary.status_label == "PASSED WITH WARNINGS":
            st.markdown(
                f'<div class="status-badge-warn" style="font-size:1.15rem; margin-bottom:12px;">⚠️ QUALITY GATE WARNING: {summary.total_warnings} warning(s) detected that require review</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-badge-fail" style="font-size:1.15rem; margin-bottom:12px;">🚫 QUALITY GATE FAILED: {summary.total_errors} error(s) must be remediated</div>',
                unsafe_allow_html=True,
            )

    # KPI Metric Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Records", summary.total_records)
    kpi2.metric("Total Issues", summary.total_issues)
    kpi3.metric("Errors (Must Fix)", summary.total_errors, delta=None)
    kpi4.metric("Warnings (Review)", summary.total_warnings, delta=None)

    # Download Report Button
    excel_stream = AttendanceValidator.generate_excel_report(df_raw, issues, summary, file_display_name)
    with col_dl:
        clean_filename = os.path.splitext(file_display_name)[0]
        st.download_button(
            label="📥 Download Excel Report",
            data=excel_stream.getvalue(),
            file_name=f"{clean_filename}_Quality_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # Visual breakdown
    if summary.total_issues > 0:
        c_chart1, c_chart2 = st.columns([2, 1])
        with c_chart1:
            st.markdown("##### Issues by Category")
            cat_df = pd.DataFrame(
                list(summary.issues_by_category.items()),
                columns=["Issue Category", "Count"],
            ).sort_values("Count", ascending=True)
            st.bar_chart(cat_df.set_index("Issue Category"), height=200)

        with c_chart2:
            st.markdown("##### Issues by Severity")
            sev_df = pd.DataFrame(
                list(summary.issues_by_severity.items()),
                columns=["Severity", "Count"],
            )
            st.bar_chart(sev_df.set_index("Severity"), height=200)

    # Tabs: Issues Table and Raw Data Explorer
    tab_issues, tab_raw = st.tabs([f"📋 Detected Issues ({summary.total_issues})", f"📄 Original Spreadsheet ({summary.total_records} rows)"])

    with tab_issues:
        if issues:
            # Filters
            f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
            with f_col1:
                severity_filter = st.selectbox("Filter by Severity:", ["All", "Error", "Warning"])
            with f_col2:
                categories = ["All"] + sorted(list(summary.issues_by_category.keys()))
                category_filter = st.selectbox("Filter by Category:", categories)
            with f_col3:
                search_query = st.text_input("Search issues (Student ID, row, or keyword):", placeholder="e.g. ENG2024-001")

            # Filter data
            issues_data = [i.to_dict() for i in issues]
            df_issues = pd.DataFrame(issues_data)

            if severity_filter != "All":
                df_issues = df_issues[df_issues["Severity"] == severity_filter]
            if category_filter != "All":
                df_issues = df_issues[df_issues["Issue Type"] == category_filter]
            if search_query:
                q = search_query.strip().lower()
                df_issues = df_issues[
                    df_issues["Student ID"].str.lower().str.contains(q, na=False)
                    | df_issues["Explanation"].str.lower().str.contains(q, na=False)
                    | df_issues["Suggested Action"].str.lower().str.contains(q, na=False)
                    | df_issues["Row Number"].astype(str).str.contains(q, na=False)
                ]

            st.markdown(f"**Showing {len(df_issues)} issue(s):**")

            # Display styled table
            st.dataframe(
                df_issues,
                use_container_width=True,
                column_config={
                    "Row Number": st.column_config.NumberColumn("Row #", width="small"),
                    "Student ID": st.column_config.TextColumn("Student ID", width="medium"),
                    "Issue Type": st.column_config.TextColumn("Issue Type", width="medium"),
                    "Severity": st.column_config.TextColumn("Severity", width="small"),
                    "Explanation": st.column_config.TextColumn("Explanation", width="large"),
                    "Suggested Action": st.column_config.TextColumn("Suggested Action", width="large"),
                },
                hide_index=True,
            )

            # Option to also download issues as CSV
            csv_issues = df_issues.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📄 Export Filtered Issues to CSV",
                data=csv_issues,
                file_name=f"{clean_filename}_issues.csv",
                mime="text/csv",
            )
        else:
            st.success("🎉 No issues detected! All records meet attendance quality gate standards.")

    with tab_raw:
        st.markdown(f"**Uploaded Data Preview: `{file_display_name}`**")
        st.dataframe(df_raw, use_container_width=True)


if __name__ == "__main__":
    main()
