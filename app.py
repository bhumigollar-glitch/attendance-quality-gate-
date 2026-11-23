"""
app.py
======
Attendance Spreadsheet Quality Gate - High-Contrast Black & White Edition (MVP)

A brutalist, high-contrast monochrome web application for auditing attendance
spreadsheets against institutional data-quality standards.
"""

import io
import os
import altair as alt
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
    page_title="Attendance Quality Gate // Monochrome",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# High-Contrast Black & White CSS
st.markdown(
    """
    <style>
    /* Global Background & Typography */
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        border-right: 1px solid #262626 !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(0, 0, 0, 0.9) !important;
    }

    /* Titles & Headers */
    .brand-title {
        font-family: "Courier New", Courier, monospace, sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        margin-bottom: 2px;
        border-bottom: 2px solid #FFFFFF;
        padding-bottom: 8px;
    }
    
    .brand-subtitle {
        font-family: monospace;
        font-size: 0.9rem;
        color: #A3A3A3;
        letter-spacing: 0.5px;
        margin-top: 6px;
        margin-bottom: 24px;
        text-transform: uppercase;
    }

    /* Metric Cards */
    .mono-card {
        background-color: #0A0A0A;
        border: 1px solid #333333;
        border-radius: 4px;
        padding: 16px;
        text-align: left;
    }
    .mono-card-title {
        font-family: monospace;
        font-size: 0.8rem;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .mono-card-val {
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
        margin-top: 4px;
    }

    /* Status Banners */
    .gate-banner-pass {
        background-color: #FFFFFF;
        color: #000000;
        border: 2px solid #FFFFFF;
        padding: 14px 20px;
        font-family: monospace;
        font-size: 1.1rem;
        font-weight: 900;
        letter-spacing: 1px;
        display: block;
        margin-bottom: 18px;
        border-radius: 4px;
    }

    .gate-banner-warn {
        background-color: #141414;
        color: #FFFFFF;
        border: 2px dashed #FFFFFF;
        padding: 14px 20px;
        font-family: monospace;
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: 1px;
        display: block;
        margin-bottom: 18px;
        border-radius: 4px;
    }

    .gate-banner-fail {
        background-color: #000000;
        color: #FFFFFF;
        border: 2px solid #FFFFFF;
        padding: 14px 20px;
        font-family: monospace;
        font-size: 1.1rem;
        font-weight: 900;
        letter-spacing: 1px;
        display: block;
        margin-bottom: 18px;
        border-radius: 4px;
        box-shadow: 0 0 15px rgba(255, 255, 255, 0.15);
    }

    /* Buttons */
    .stButton > button {
        background-color: #0A0A0A !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 3px !important;
        font-family: monospace !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.15s ease-in-out !important;
    }

    .stButton > button:hover {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #FFFFFF !important;
        transform: translateY(-1px);
    }

    .stDownloadButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 3px !important;
        font-family: monospace !important;
        font-size: 0.85rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.15s ease-in-out !important;
    }

    .stDownloadButton > button:hover {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }

    /* Tabs Styling */
    button[data-baseweb="tab"] {
        font-family: monospace !important;
        font-size: 0.9rem !important;
        color: #888888 !important;
        border-bottom: 2px solid transparent !important;
        padding: 10px 16px !important;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        border-bottom: 2px solid #FFFFFF !important;
        font-weight: 800 !important;
    }

    /* Expanders & Inputs */
    [data-testid="stExpander"] {
        background-color: #0A0A0A !important;
        border: 1px solid #262626 !important;
        border-radius: 4px !important;
    }

    /* File uploader container */
    [data-testid="stFileUploader"] {
        border: 1px dashed #444444 !important;
        padding: 12px !important;
        border-radius: 4px !important;
        background-color: #0A0A0A !important;
    }

    /* Dataframe borders */
    [data-testid="stDataFrame"] {
        border: 1px solid #333333 !important;
        border-radius: 4px;
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
            xl = pd.ExcelFile(uploaded_file)
            if len(xl.sheet_names) > 1:
                st.sidebar.caption(f"MULTIPLE SHEETS FOUND: Reading '{xl.sheet_names[0]}'.")
            df = xl.parse(xl.sheet_names[0])
        else:
            st.error("UNSUPPORTED FORMAT: Please upload .xlsx, .xls, or .csv")
            return None
        return df
    except Exception as e:
        st.error(f"FILE READ ERROR: {str(e)}")
        return None


def render_monochrome_bar_chart(data: pd.DataFrame, x_col: str, y_col: str, title: str):
    """Renders a clean high-contrast black & white bar chart using Altair."""
    chart = (
        alt.Chart(data)
        .mark_bar(color="#FFFFFF", stroke="#000000", strokeWidth=1)
        .encode(
            x=alt.X(f"{x_col}:O", sort="-y", title="", axis=alt.Axis(labelColor="#CCCCCC", labelFont="monospace", labelAngle=-20)),
            y=alt.Y(f"{y_col}:Q", title="Count", axis=alt.Axis(labelColor="#CCCCCC", labelFont="monospace", gridColor="#222222", tickColor="#555555")),
            tooltip=[x_col, y_col],
        )
        .properties(height=200, title=alt.TitleParams(text=title, color="#FFFFFF", font="monospace", fontSize=12))
        .configure_view(strokeOpacity=0)
    )
    st.altair_chart(chart, use_container_width=True)


def main():
    # Header Banner
    st.markdown('<div class="brand-title">ATTENDANCE QUALITY GATE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">// DETERMINISTIC COMPLIANCE AUDIT & DATA VERIFICATION ENGINE</div>',
        unsafe_allow_html=True,
    )

    # Sidebar: File Upload & Configuration
    with st.sidebar:
        st.markdown("### `[ 01 // UPLOAD ]`")
        uploaded_file = st.file_uploader(
            "Select Attendance Spreadsheet",
            type=["xlsx", "xls", "csv"],
            help="Upload college attendance records in Excel (.xlsx, .xls) or CSV (.csv) format.",
        )

        st.markdown("---")
        st.markdown("### `[ 02 // DUMMY DATA ]`")
        st.caption("One-click testing with preloaded synthetic datasets:")

        col_s1, col_s2 = st.columns(2)
        sample_path_messy = os.path.join(os.path.dirname(__file__), "sample_data", "attendance.xlsx")
        sample_path_clean = os.path.join(os.path.dirname(__file__), "sample_data", "attendance_clean.xlsx")

        load_sample = False
        sample_type = None
        if col_s1.button("⚠ WITH ERRORS", use_container_width=True, help="Load synthetic attendance with deliberate edge cases."):
            load_sample = True
            sample_type = "messy"
        if col_s2.button("✓ 100% CLEAN", use_container_width=True, help="Load 100% clean attendance records."):
            load_sample = True
            sample_type = "clean"

        # Download buttons for dummy files to disk
        st.caption("Or download dummy files to disk:")
        if os.path.exists(sample_path_messy):
            with open(sample_path_messy, "rb") as f_m:
                st.download_button(
                    label="↓ GET DUMMY (.XLSX)",
                    data=f_m.read(),
                    file_name="sample_attendance_with_errors.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        if os.path.exists(sample_path_clean):
            with open(sample_path_clean, "rb") as f_c:
                st.download_button(
                    label="↓ GET CLEAN (.XLSX)",
                    data=f_c.read(),
                    file_name="sample_attendance_clean.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        st.markdown("---")
        st.markdown("### `[ 03 // PARAMETERS ]`")
        pct_tolerance = st.slider(
            "Percentage Tolerance (±%)",
            min_value=0.0,
            max_value=2.0,
            value=0.5,
            step=0.1,
            help="Allowable rounding difference between reported and calculated attendance percentage.",
        )

        st.markdown("---")
        st.markdown("### `[ RULES ENFORCED ]`")
        st.markdown(
            """
            - `RULE 01`: Missing Values
            - `RULE 02`: Duplicate Records
            - `RULE 03`: Invalid Counts
            - `RULE 04`: Percentage Math
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
            st.sidebar.caption(f"ACTIVE DATASET: `{file_display_name}`")
        else:
            st.warning("Sample data file not found on disk.")

    if df_raw is None:
        # Welcome Guide in stark black and white
        st.markdown(
            """
            <div style="border: 1px solid #333333; padding: 24px; background-color: #0A0A0A; border-radius: 4px;">
                <h3 style="margin-top:0; font-family: monospace; letter-spacing: 1px;">AWAITING SPREADSHEET INPUT</h3>
                <p style="color: #A3A3A3; font-size: 0.95rem;">
                    Upload an Excel (<code>.xlsx</code>, <code>.xls</code>) or CSV (<code>.csv</code>) file via the sidebar, 
                    or click <b>"WITH ERRORS"</b> / <b>"100% CLEAN"</b> to evaluate synthetic benchmarks immediately.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            st.markdown(
                """
                <div class="mono-card">
                    <div class="mono-card-title">01 // INGESTION</div>
                    <div style="margin-top: 10px; color: #CCCCCC; font-size: 0.9rem;">
                        Automated mapping of student identifiers, course codes, session counts, and attendance ratios.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_w2:
            st.markdown(
                """
                <div class="mono-card">
                    <div class="mono-card-title">02 // DETERMINISTIC AUDIT</div>
                    <div style="margin-top: 10px; color: #CCCCCC; font-size: 0.9rem;">
                        4-rule deterministic gate: Missing values, accidental duplicates, count overflows, and percentage math.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_w3:
            st.markdown(
                """
                <div class="mono-card">
                    <div class="mono-card-title">03 // AUDIT REPORT</div>
                    <div style="margin-top: 10px; color: #CCCCCC; font-size: 0.9rem;">
                        Pass/Fail gate status, drill-down table with suggested remediation, and exportable multi-sheet Excel reports.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### `[ RULE DEFINITION MATRIX ]`")
        rule_data = [
            {"Rule Code": "R01", "Rule Name": "Missing Values", "Criteria": "Student ID, Subject, Held, or Attended missing/empty", "Severity": "ERROR"},
            {"Rule Code": "R02", "Rule Name": "Duplicate Records", "Criteria": "Repeated student in same course session (multi-course preserved)", "Severity": "WARNING"},
            {"Rule Code": "R03", "Rule Name": "Invalid Attendance", "Criteria": "Attended < 0, Held < 0, Attended > Held, or non-numeric count", "Severity": "ERROR"},
            {"Rule Code": "R04", "Rule Name": "Percentage Validation", "Criteria": "Reported % deviates from (Attended/Held)*100; safe 0-held logic", "Severity": "WARNING"},
        ]
        st.dataframe(pd.DataFrame(rule_data), use_container_width=True, hide_index=True)
        return

    # Column Mapping Expander
    with st.expander("▾ COLUMN MAPPING AUDIT [AUTO-DETECTED]", expanded=False):
        detected_mapping = AttendanceValidator.detect_columns(df_raw)
        col_m1, col_m2 = st.columns(2)

        custom_mapping = {}
        all_cols = ["-- Not Present --"] + list(df_raw.columns)

        with col_m1:
            for field in ["student_id", "subject", "classes_held"]:
                default_val = detected_mapping.get(field)
                idx = all_cols.index(default_val) if default_val in all_cols else 0
                custom_mapping[field] = st.selectbox(
                    f"Mapped Column for '{field.replace('_', ' ').upper()}'",
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
                    f"Mapped Column for '{field.replace('_', ' ').upper()}'",
                    options=all_cols,
                    index=idx,
                    key=f"col_map_{field}",
                )
                if custom_mapping[field] == "-- Not Present --":
                    custom_mapping[field] = None

    # Run Validation Engine
    validator = AttendanceValidator(
        percentage_tolerance=pct_tolerance,
    )
    issues, summary = validator.validate(df_raw, custom_mapping=custom_mapping)

    # Section: Gate Summary & KPIs
    st.markdown("### `[ QUALITY GATE SUMMARY ]`")

    # Status Banner
    col_status, col_dl = st.columns([3, 1])
    with col_status:
        if summary.status_label == "PASSED":
            st.markdown(
                '<div class="gate-banner-pass">✓ QUALITY GATE PASSED // SPREADSHEET CERTIFIED CLEAN (0 ISSUES)</div>',
                unsafe_allow_html=True,
            )
        elif summary.status_label == "PASSED WITH WARNINGS":
            st.markdown(
                f'<div class="gate-banner-warn">⚠ QUALITY GATE WARNING // {summary.total_warnings} WARNING(S) REQUIRE ADMINISTRATIVE REVIEW</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="gate-banner-fail">✕ QUALITY GATE FAILED // {summary.total_errors} CRITICAL ERROR(S) REQUIRE REMEDIATION</div>',
                unsafe_allow_html=True,
            )

    # Download Report Button
    excel_stream = AttendanceValidator.generate_excel_report(df_raw, issues, summary, file_display_name)
    with col_dl:
        clean_filename = os.path.splitext(file_display_name)[0]
        st.download_button(
            label="↓ EXCEL REPORT",
            data=excel_stream.getvalue(),
            file_name=f"{clean_filename}_Quality_Audit_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # KPI Metric Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(
            f"""
            <div class="mono-card">
                <div class="mono-card-title">TOTAL RECORDS</div>
                <div class="mono-card-val">{summary.total_records}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi2:
        st.markdown(
            f"""
            <div class="mono-card">
                <div class="mono-card-title">TOTAL ISSUES</div>
                <div class="mono-card-val">{summary.total_issues}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi3:
        st.markdown(
            f"""
            <div class="mono-card">
                <div class="mono-card-title">CRITICAL ERRORS</div>
                <div class="mono-card-val">{summary.total_errors}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi4:
        st.markdown(
            f"""
            <div class="mono-card">
                <div class="mono-card-title">WARNINGS</div>
                <div class="mono-card-val">{summary.total_warnings}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Visual Breakdown (Altair monochrome charts)
    if summary.total_issues > 0:
        c_chart1, c_chart2 = st.columns([2, 1])
        with c_chart1:
            cat_df = pd.DataFrame(
                list(summary.issues_by_category.items()),
                columns=["Category", "Count"],
            )
            render_monochrome_bar_chart(cat_df, "Category", "Count", "ISSUES BY CATEGORY")

        with c_chart2:
            sev_df = pd.DataFrame(
                list(summary.issues_by_severity.items()),
                columns=["Severity", "Count"],
            )
            render_monochrome_bar_chart(sev_df, "Severity", "Count", "ISSUES BY SEVERITY")

    # Tabs: Issues Table and Raw Data Explorer
    tab_issues, tab_raw = st.tabs([
        f"DETECTED ISSUES [{summary.total_issues}]",
        f"SPREADSHEET RECORDS [{summary.total_records}]"
    ])

    with tab_issues:
        if issues:
            f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
            with f_col1:
                severity_filter = st.selectbox("FILTER SEVERITY:", ["All", "Error", "Warning"])
            with f_col2:
                categories = ["All"] + sorted(list(summary.issues_by_category.keys()))
                category_filter = st.selectbox("FILTER CATEGORY:", categories)
            with f_col3:
                search_query = st.text_input("SEARCH AUDIT TRAIL:", placeholder="Filter by Student ID, row, or keyword...")

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

            st.caption(f"Displaying {len(df_issues)} of {summary.total_issues} issue(s):")

            st.dataframe(
                df_issues,
                use_container_width=True,
                column_config={
                    "Row Number": st.column_config.NumberColumn("ROW #", width="small"),
                    "Student ID": st.column_config.TextColumn("STUDENT ID", width="medium"),
                    "Issue Type": st.column_config.TextColumn("ISSUE CATEGORY", width="medium"),
                    "Severity": st.column_config.TextColumn("SEVERITY", width="small"),
                    "Explanation": st.column_config.TextColumn("AUDIT EXPLANATION", width="large"),
                    "Suggested Action": st.column_config.TextColumn("RECOMMENDED ACTION", width="large"),
                },
                hide_index=True,
            )

            # CSV Download
            csv_issues = df_issues.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="↓ EXPORT FILTERED ISSUES TO CSV",
                data=csv_issues,
                file_name=f"{clean_filename}_issues_audit.csv",
                mime="text/csv",
            )
        else:
            st.markdown(
                """
                <div style="border: 1px solid #FFFFFF; padding: 20px; background-color: #0A0A0A; border-radius: 4px; text-align: center;">
                    <h4 style="margin: 0; font-family: monospace; letter-spacing: 1px;">✓ 0 ANOMALIES DETECTED // 100% QUALITY GATE COMPLIANT</h4>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_raw:
        st.caption(f"RAW RECORD MATRIX // SOURCE: `{file_display_name}`")
        st.dataframe(df_raw, use_container_width=True)


if __name__ == "__main__":
    main()
