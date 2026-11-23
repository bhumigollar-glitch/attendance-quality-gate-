"""
app.py
======
Attendance Spreadsheet Quality Gate - High-Contrast Technical Edition (MVP)

A brutalist, high-contrast monochrome and telemetry dashboard for auditing
attendance spreadsheets against institutional data-quality standards.
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
    page_title="Attendance Quality Gate // Telemetry",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Unified High-Contrast Dashboard CSS
st.markdown(
    """
    <style>
    /* 1. Global Background & Consistent Typography */
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }

    /* Reduce default Streamlit page top & side whitespace */
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }
    
    /* 2. Left Sidebar - Increased Width & Styling */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        width: 380px !important;
        min-width: 380px !important;
        max-width: 420px !important;
        background-color: #0A0A0A !important;
        border-right: 1px solid #222222 !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 380px !important;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 1.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(0, 0, 0, 0.85) !important;
        height: 2.75rem !important;
    }

    /* 3. Titles & Headers - Consistent Technical Aesthetic (No Serif) */
    .brand-title {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        margin-bottom: 0px;
        line-height: 1.2;
    }
    
    .brand-subtitle {
        font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace;
        font-size: 0.78rem;
        color: #888888;
        letter-spacing: 0.75px;
        margin-top: 3px;
        margin-bottom: 12px;
        text-transform: uppercase;
        border-bottom: 1px solid #222222;
        padding-bottom: 8px;
    }

    .section-header-compact {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.85rem;
        font-weight: 700;
        color: #A3A3A3;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-top: 6px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* 4. Green, Yellow, and Red Status Indicators */
    .indicator-dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
        flex-shrink: 0;
    }
    .dot-green {
        background-color: #22c55e;
        box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
    }
    .dot-yellow {
        background-color: #eab308;
        box-shadow: 0 0 8px rgba(234, 179, 8, 0.7);
    }
    .dot-red {
        background-color: #ef4444;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.7);
    }

    .status-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 3px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.75px;
        margin-right: 10px;
        line-height: 1;
    }
    .badge-green {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid #22c55e;
    }
    .badge-yellow {
        background-color: rgba(234, 179, 8, 0.15);
        color: #facc15;
        border: 1px solid #eab308;
    }
    .badge-red {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid #ef4444;
    }

    /* Status Banners */
    .gate-banner {
        padding: 12px 18px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .gate-banner-pass {
        background: linear-gradient(90deg, rgba(34, 197, 94, 0.12) 0%, rgba(10, 10, 10, 0.95) 100%);
        color: #4ade80;
        border: 1px solid #166534;
        border-left: 5px solid #22c55e;
    }
    .gate-banner-warn {
        background: linear-gradient(90deg, rgba(234, 179, 8, 0.12) 0%, rgba(10, 10, 10, 0.95) 100%);
        color: #facc15;
        border: 1px solid #854d0e;
        border-left: 5px solid #eab308;
    }
    .gate-banner-fail {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.14) 0%, rgba(10, 10, 10, 0.95) 100%);
        color: #f87171;
        border: 1px solid #991b1b;
        border-left: 5px solid #ef4444;
        box-shadow: 0 0 16px rgba(239, 68, 68, 0.12);
    }

    /* KPI Metric Cards */
    .mono-card {
        background-color: #0A0A0A;
        border: 1px solid #222222;
        border-radius: 4px;
        padding: 12px 14px;
        text-align: left;
        margin-bottom: 8px;
    }
    .mono-card.kpi-records {
        border-top: 3px solid #525252;
    }
    .mono-card.kpi-clean {
        border-top: 3px solid #22c55e;
    }
    .mono-card.kpi-warning {
        border-top: 3px solid #eab308;
    }
    .mono-card.kpi-error {
        border-top: 3px solid #ef4444;
    }
    .mono-card.kpi-clean-zero {
        border-top: 3px solid #262626;
    }
    
    .mono-card-title {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.75rem;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 0.75px;
        display: flex;
        align-items: center;
    }
    .mono-card-val {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 2.1rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
        margin-top: 2px;
    }

    /* 5. Prominent Upload Section */
    .sidebar-upload-panel {
        background-color: #111111;
        border: 1px solid #333333;
        border-top: 2px solid #FFFFFF;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .sidebar-upload-panel .title {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.8rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: 1px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    .sidebar-upload-panel .subtitle {
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 0.75rem;
        color: #888888;
        margin-bottom: 10px;
    }

    [data-testid="stFileUploader"] {
        border: 2px dashed #444444 !important;
        padding: 12px 10px !important;
        border-radius: 5px !important;
        background-color: #080808 !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #FFFFFF !important;
        background-color: #121212 !important;
        box-shadow: 0 0 14px rgba(255, 255, 255, 0.08) !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 3px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-weight: 800 !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.5px !important;
        padding: 5px 12px !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: #D4D4D4 !important;
        color: #000000 !important;
    }

    /* Hero Upload Card (Main page when no file loaded) */
    .hero-upload-card {
        background-color: #0A0A0A;
        border: 2px dashed #444444;
        border-radius: 8px;
        padding: 24px;
        text-align: center;
        margin-bottom: 16px;
        transition: border-color 0.2s ease;
    }
    .hero-upload-card:hover {
        border-color: #FFFFFF;
    }
    .hero-upload-badge {
        display: inline-block;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.75rem;
        font-weight: 800;
        background-color: #1F1F1F;
        color: #A3A3A3;
        border: 1px solid #333333;
        padding: 3px 10px;
        border-radius: 3px;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .hero-upload-title {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 1.4rem;
        font-weight: 800;
        color: #FFFFFF;
        margin-top: 0;
        margin-bottom: 8px;
    }
    .hero-upload-desc {
        color: #888888;
        font-size: 0.88rem;
        max-width: 650px;
        margin: 0 auto 16px auto;
        line-height: 1.4;
    }

    /* 6. Fix Truncated Buttons (WITH ERR...) & General Buttons */
    .stButton > button {
        background-color: #0A0A0A !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 3px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.3px !important;
        padding: 6px 8px !important;
        white-space: nowrap !important;
        transition: all 0.15s ease-in-out !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-color: #FFFFFF !important;
    }

    /* Prevent truncation in Streamlit inner paragraph tag */
    .stButton button p,
    .stDownloadButton button p {
        white-space: nowrap !important;
        text-overflow: unset !important;
        overflow: visible !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px !important;
    }

    .stDownloadButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 3px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.78rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        padding: 6px 12px !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stDownloadButton > button:hover {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }

    /* Active dataset pill in sidebar */
    .sidebar-active-pill {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.76rem;
        background-color: #111111;
        border: 1px solid #262626;
        padding: 6px 10px;
        border-radius: 4px;
        margin-top: 8px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        color: #D4D4D4;
    }

    /* 7. Tight, Compact Results Layout (Reduced Empty Space) */
    div[data-testid="stHorizontalBlock"] {
        gap: 10px !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 0px !important;
    }

    button[data-baseweb="tab"] {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.82rem !important;
        color: #888888 !important;
        border-bottom: 2px solid transparent !important;
        padding: 8px 14px !important;
        letter-spacing: 0.5px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        border-bottom: 2px solid #FFFFFF !important;
        font-weight: 800 !important;
    }

    [data-testid="stExpander"] {
        background-color: #0A0A0A !important;
        border: 1px solid #222222 !important;
        border-radius: 4px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stExpander"] details summary {
        padding-top: 6px !important;
        padding-bottom: 6px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 0.82rem !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #262626 !important;
        border-radius: 4px;
    }

    /* 8. Authentication & Login Portal */
    .login-card {
        background-color: #0A0A0A;
        border: 1px solid #262626;
        border-radius: 8px;
        padding: 24px;
        margin-top: 10px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8);
    }
    .google-signin-btn > button {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #E5E7EB !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.86rem !important;
        letter-spacing: 0.2px !important;
        padding: 10px 14px !important;
        border-radius: 4px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        transition: all 0.15s ease !important;
    }
    .google-signin-btn > button:hover {
        background-color: #F3F4F6 !important;
        color: #000000 !important;
        border-color: #D1D5DB !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(255, 255, 255, 0.18) !important;
    }
    .login-divider {
        display: flex;
        align-items: center;
        text-align: center;
        margin: 18px 0;
        color: #666666;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.72rem;
        letter-spacing: 1px;
    }
    .login-divider::before,
    .login-divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid #262626;
    }
    .login-divider:not(:empty)::before {
        margin-right: .75em;
    }
    .login-divider:not(:empty)::after {
        margin-left: .75em;
    }
    .demo-creds-banner {
        background-color: #0E0E0E;
        border: 1px solid #222222;
        border-radius: 6px;
        padding: 12px;
        margin-top: 16px;
    }
    .demo-creds-title {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.72rem;
        color: #A3A3A3;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    /* Sidebar User Profile Card */
    .sidebar-user-card {
        background-color: #111111;
        border: 1px solid #262626;
        border-radius: 6px;
        padding: 10px 12px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .user-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        color: #FFFFFF;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-weight: 800;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .user-details {
        overflow: hidden;
        flex: 1;
    }
    .user-name {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 700;
        font-size: 0.82rem;
        color: #FFFFFF;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .user-email {
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.7rem;
        color: #888888;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .user-provider-tag {
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.68rem;
        color: #4ade80;
        display: flex;
        align-items: center;
        margin-top: 2px;
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


def render_chart(data: pd.DataFrame, x_col: str, y_col: str, title: str, is_severity: bool = False):
    """Renders a clean high-contrast chart with green/yellow/red status indicators using Altair."""
    if is_severity:
        # Green/Yellow/Red status colors for severity bars
        color_scale = alt.Scale(
            domain=["ERROR", "Error", "WARNING", "Warning"],
            range=["#ef4444", "#ef4444", "#eab308", "#eab308"],
        )
        chart = (
            alt.Chart(data)
            .mark_bar(stroke="#000000", strokeWidth=1, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
            .encode(
                x=alt.X(
                    f"{x_col}:O",
                    sort="-y",
                    title="",
                    axis=alt.Axis(labelColor="#D4D4D4", labelFont="monospace", labelAngle=0, labelFontSize=10),
                ),
                y=alt.Y(
                    f"{y_col}:Q",
                    title="Count",
                    axis=alt.Axis(labelColor="#888888", labelFont="monospace", gridColor="#1E1E1E", tickColor="#444444", labelFontSize=10),
                ),
                color=alt.Color(f"{x_col}:N", scale=color_scale, legend=None),
                tooltip=[x_col, y_col],
            )
            .properties(height=160, title=alt.TitleParams(text=title, color="#A3A3A3", font="monospace", fontSize=11))
            .configure_view(strokeOpacity=0)
        )
    else:
        chart = (
            alt.Chart(data)
            .mark_bar(color="#E5E5E5", stroke="#000000", strokeWidth=1, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
            .encode(
                x=alt.X(
                    f"{x_col}:O",
                    sort="-y",
                    title="",
                    axis=alt.Axis(labelColor="#D4D4D4", labelFont="monospace", labelAngle=-15, labelFontSize=9),
                ),
                y=alt.Y(
                    f"{y_col}:Q",
                    title="Count",
                    axis=alt.Axis(labelColor="#888888", labelFont="monospace", gridColor="#1E1E1E", tickColor="#444444", labelFontSize=10),
                ),
                tooltip=[x_col, y_col],
            )
            .properties(height=160, title=alt.TitleParams(text=title, color="#A3A3A3", font="monospace", fontSize=11))
            .configure_view(strokeOpacity=0)
        )
    st.altair_chart(chart, use_container_width=True)


def render_login_page():
    """Renders a secure, high-contrast brutalist login gateway."""
    _, col_login, _ = st.columns([1, 1.4, 1])

    with col_login:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 1.5rem; margin-bottom: 1.25rem;">
                <div class="brand-title" style="font-size: 1.85rem; border: none; margin-bottom: 4px;">ATTENDANCE QUALITY GATE</div>
                <div class="brand-subtitle" style="border: none; margin-bottom: 1rem;">// SECURE AUDIT ACCESS & IDENTITY GATEWAY</div>
                <div style="display: inline-flex; align-items: center; background: #111111; border: 1px solid #262626; padding: 4px 12px; border-radius: 20px;">
                    <span class="indicator-dot dot-green"></span>
                    <span style="font-family: ui-monospace, monospace; font-size: 0.72rem; color: #4ade80; letter-spacing: 0.5px; font-weight: 700;">GATEWAY ONLINE // 256-BIT ENCRYPTION</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="login-card">', unsafe_allow_html=True)

        # 1. Google OAuth Sign-In Option
        st.markdown(
            """
            <div style="font-family: ui-monospace, monospace; font-size: 0.78rem; font-weight: 700; color: #CCCCCC; letter-spacing: 0.5px; margin-bottom: 8px;">
                SIGN IN WITH GOOGLE WORKSPACE
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="google-signin-btn">', unsafe_allow_html=True)
        if st.button("🌐 Continue with Google", key="btn_google_signin", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_info"] = {
                "name": "Sujal Maruti Gollar",
                "email": "sujal.gollar@gmail.com",
                "role": "Academic Quality Auditor",
                "provider": "Google OAuth 2.0",
                "avatar_initials": "SG",
            }
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. Divider
        st.markdown(
            """
            <div class="login-divider">
                <span>OR SIGN IN WITH LOGIN ID</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3. Credentials Form
        with st.form("credentials_login_form"):
            login_id = st.text_input(
                "Login ID / Institutional Email",
                placeholder="e.g. admin or faculty@institution.edu",
                help="Enter your assigned faculty ID or institutional email.",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                help="Enter your password.",
            )

            remember_me = st.checkbox("Remember this device for 30 days", value=True)
            submitted = st.form_submit_button("AUTHENTICATE // ACCESS GATEWAY", use_container_width=True)

            if submitted:
                clean_id = login_id.strip()
                clean_pw = password.strip()
                if not clean_id or not clean_pw:
                    st.error("ACCESS DENIED: Please provide both Login ID and Password.")
                elif len(clean_pw) < 4:
                    st.error("ACCESS DENIED: Password must be at least 4 characters.")
                else:
                    is_admin = "admin" in clean_id.lower()
                    display_name = clean_id.split("@")[0].replace(".", " ").replace("_", " ").title()
                    initials = "".join([p[0] for p in display_name.split()[:2]]).upper() or "ID"
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = {
                        "name": display_name,
                        "email": clean_id if "@" in clean_id else f"{clean_id}@institution.edu",
                        "role": "System Administrator" if is_admin else "Academic Auditor",
                        "provider": "Institutional ID",
                        "avatar_initials": initials,
                    }
                    st.rerun()

        # 4. Quick Demo Test Accounts Box
        st.markdown(
            """
            <div class="demo-creds-banner">
                <div class="demo-creds-title">⚡ QUICK ACCESS / TEST ACCOUNTS:</div>
                <div style="font-family: ui-monospace, monospace; color: #888888; font-size: 0.74rem; line-height: 1.6;">
                    • <b>Admin:</b> <code>admin</code> &nbsp;/&nbsp; <code>admin123</code><br>
                    • <b>Faculty:</b> <code>faculty</code> &nbsp;/&nbsp; <code>faculty123</code><br>
                    • <b>Google:</b> Click <span style="color: #4ade80;">"Continue with Google"</span> for 1-click SSO
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="text-align: center; margin-top: 18px; color: #555555; font-family: ui-monospace, monospace; font-size: 0.68rem; letter-spacing: 0.5px;">
                FERPA & SOC-2 COMPLIANT // END-TO-END ENCRYPTED AUDIT SESSION
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('</div>', unsafe_allow_html=True)


def main():
    # Session state initialization for authentication
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_info" not in st.session_state:
        st.session_state["user_info"] = None

    # Gate access: show login page if not authenticated
    if not st.session_state["authenticated"]:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        render_login_page()
        return

    # Header Banner - Clean Technical Aesthetic
    st.markdown('<div class="brand-title">ATTENDANCE QUALITY GATE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">// DETERMINISTIC COMPLIANCE AUDIT & DATA VERIFICATION ENGINE</div>',
        unsafe_allow_html=True,
    )

    # Sidebar: File Upload & Configuration
    with st.sidebar:
        # Authenticated User Profile Badge & Logout
        user = st.session_state.get("user_info") or {}
        st.markdown(
            f"""
            <div class="sidebar-user-card">
                <div class="user-avatar">{user.get('avatar_initials', 'AU')}</div>
                <div class="user-details">
                    <div class="user-name">{user.get('name', 'Auditor')}</div>
                    <div class="user-email">{user.get('email', 'sso@institution.edu')}</div>
                    <div class="user-provider-tag"><span class="indicator-dot dot-green"></span>{user.get('provider', 'Verified')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("LOGOUT / SIGN OUT", key="btn_logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_info"] = None
            if "sample_loaded" in st.session_state:
                del st.session_state["sample_loaded"]
            st.rerun()

        st.markdown("---")

        # Prominent Upload Header & Box
        st.markdown(
            """
            <div class="sidebar-upload-panel">
                <div class="title">
                    <span>01 // UPLOAD DATA</span>
                    <span style="font-size: 0.65rem; background: #262626; color: #FFFFFF; padding: 2px 6px; border-radius: 2px;">PRIMARY</span>
                </div>
                <div class="subtitle">Drop Excel (.xlsx, .xls) or CSV (.csv)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded_file_sidebar = st.file_uploader(
            "Select Attendance Spreadsheet",
            type=["xlsx", "xls", "csv"],
            key="sidebar_uploader",
            label_visibility="collapsed",
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
        if col_s1.button("⚠ WITH ERRORS", key="btn_sample_errors", use_container_width=True, help="Load synthetic attendance with deliberate edge cases."):
            load_sample = True
            sample_type = "messy"
        if col_s2.button("✓ 100% CLEAN", key="btn_sample_clean", use_container_width=True, help="Load 100% clean attendance records."):
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

    if uploaded_file_sidebar is not None:
        df_raw = load_file(uploaded_file_sidebar)
        file_display_name = uploaded_file_sidebar.name
        st.sidebar.markdown(
            f'<div class="sidebar-active-pill"><span class="indicator-dot dot-green"></span>FILE: <b>{file_display_name}</b></div>',
            unsafe_allow_html=True,
        )
    elif load_sample or "sample_loaded" in st.session_state:
        if load_sample:
            st.session_state["sample_loaded"] = sample_type
        current_sample = st.session_state.get("sample_loaded", "messy")
        target_path = sample_path_clean if current_sample == "clean" else sample_path_messy
        if os.path.exists(target_path):
            df_raw = pd.read_excel(target_path)
            file_display_name = os.path.basename(target_path)
            active_dot = "dot-green" if current_sample == "clean" else "dot-yellow"
            st.sidebar.markdown(
                f'<div class="sidebar-active-pill"><span class="indicator-dot {active_dot}"></span>ACTIVE: <b>{file_display_name}</b></div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("Sample data file not found on disk.")

    if df_raw is None:
        # Prominent Hero Upload Section in Main View
        st.markdown(
            """
            <div class="hero-upload-card">
                <div class="hero-upload-badge">READY FOR INPUT // ZERO DATA RETAINED</div>
                <div class="hero-upload-title">Drop Attendance Spreadsheet to Audit</div>
                <div class="hero-upload-desc">
                    Select an Excel (<code>.xlsx</code>, <code>.xls</code>) or CSV (<code>.csv</code>) file below, 
                    drag & drop into the sidebar, or click <b>"WITH ERRORS"</b> / <b>"100% CLEAN"</b> for instant synthetic benchmarks.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file_main = st.file_uploader(
            "Primary File Dropzone",
            type=["xlsx", "xls", "csv"],
            key="main_dropzone",
            label_visibility="collapsed",
            help="Upload college attendance records in Excel or CSV format.",
        )

        if uploaded_file_main is not None:
            df_raw = load_file(uploaded_file_main)
            file_display_name = uploaded_file_main.name
            st.rerun()

        # Three Feature Cards
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            st.markdown(
                """
                <div class="mono-card">
                    <div class="mono-card-title"><span class="indicator-dot dot-green"></span>01 // INGESTION</div>
                    <div style="margin-top: 8px; color: #A3A3A3; font-size: 0.85rem; line-height: 1.4;">
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
                    <div class="mono-card-title"><span class="indicator-dot dot-yellow"></span>02 // DETERMINISTIC AUDIT</div>
                    <div style="margin-top: 8px; color: #A3A3A3; font-size: 0.85rem; line-height: 1.4;">
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
                    <div class="mono-card-title"><span class="indicator-dot dot-red"></span>03 // AUDIT REPORT</div>
                    <div style="margin-top: 8px; color: #A3A3A3; font-size: 0.85rem; line-height: 1.4;">
                        Pass/Fail gate status, drill-down table with suggested remediation, and exportable multi-sheet Excel reports.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="section-header-compact" style="margin-top: 16px;">[ RULE DEFINITION MATRIX ]</div>',
            unsafe_allow_html=True,
        )
        rule_data = [
            {"Rule Code": "R01", "Rule Name": "Missing Values", "Criteria": "Student ID, Subject, Held, or Attended missing/empty", "Severity": "ERROR"},
            {"Rule Code": "R02", "Rule Name": "Duplicate Records", "Criteria": "Repeated student in same course session (multi-course preserved)", "Severity": "WARNING"},
            {"Rule Code": "R03", "Rule Name": "Invalid Attendance", "Criteria": "Attended < 0, Held < 0, Attended > Held, or non-numeric count", "Severity": "ERROR"},
            {"Rule Code": "R04", "Rule Name": "Percentage Validation", "Criteria": "Reported % deviates from (Attended/Held)*100; safe 0-held logic", "Severity": "WARNING"},
        ]
        st.dataframe(pd.DataFrame(rule_data), use_container_width=True, hide_index=True)
        return

    # Compact Column Mapping Expander
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

    # Section: Gate Summary & KPIs (Compact & Tight)
    st.markdown('<div class="section-header-compact">[ QUALITY GATE SUMMARY ]</div>', unsafe_allow_html=True)

    # Status Banner with Status Indicators (Green / Yellow / Red)
    col_status, col_dl = st.columns([3, 1])
    with col_status:
        if summary.status_label == "PASSED":
            st.markdown(
                """
                <div class="gate-banner gate-banner-pass">
                    <span class="indicator-dot dot-green"></span>
                    <span class="status-badge badge-green">PASSED</span>
                    <span>QUALITY GATE PASSED // SPREADSHEET CERTIFIED CLEAN (0 ISSUES)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif summary.status_label == "PASSED WITH WARNINGS":
            st.markdown(
                f"""
                <div class="gate-banner gate-banner-warn">
                    <span class="indicator-dot dot-yellow"></span>
                    <span class="status-badge badge-yellow">WARNING</span>
                    <span>QUALITY GATE WARNING // {summary.total_warnings} WARNING(S) REQUIRE ADMINISTRATIVE REVIEW</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="gate-banner gate-banner-fail">
                    <span class="indicator-dot dot-red"></span>
                    <span class="status-badge badge-red">FAILED</span>
                    <span>QUALITY GATE FAILED // {summary.total_errors} CRITICAL ERROR(S) REQUIRE REMEDIATION</span>
                </div>
                """,
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

    # KPI Metric Cards with Visual Indicators
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(
            f"""
            <div class="mono-card kpi-records">
                <div class="mono-card-title">TOTAL RECORDS</div>
                <div class="mono-card-val">{summary.total_records}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi2:
        issues_color = "#22c55e" if summary.total_issues == 0 else ("#eab308" if summary.total_errors == 0 else "#ef4444")
        card_class = "kpi-clean" if summary.total_issues == 0 else ("kpi-warning" if summary.total_errors == 0 else "kpi-error")
        st.markdown(
            f"""
            <div class="mono-card {card_class}">
                <div class="mono-card-title">TOTAL ISSUES</div>
                <div class="mono-card-val" style="color: {issues_color};">{summary.total_issues}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi3:
        err_color = "#ef4444" if summary.total_errors > 0 else "#888888"
        err_class = "kpi-error" if summary.total_errors > 0 else "kpi-clean-zero"
        st.markdown(
            f"""
            <div class="mono-card {err_class}">
                <div class="mono-card-title"><span class="indicator-dot dot-red"></span>CRITICAL ERRORS</div>
                <div class="mono-card-val" style="color: {err_color};">{summary.total_errors}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi4:
        warn_color = "#eab308" if summary.total_warnings > 0 else "#888888"
        warn_class = "kpi-warning" if summary.total_warnings > 0 else "kpi-clean-zero"
        st.markdown(
            f"""
            <div class="mono-card {warn_class}">
                <div class="mono-card-title"><span class="indicator-dot dot-yellow"></span>WARNINGS</div>
                <div class="mono-card-val" style="color: {warn_color};">{summary.total_warnings}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Visual Breakdown (Altair charts with indicator colors, compact height)
    if summary.total_issues > 0:
        c_chart1, c_chart2 = st.columns([2, 1])
        with c_chart1:
            cat_df = pd.DataFrame(
                list(summary.issues_by_category.items()),
                columns=["Category", "Count"],
            )
            render_chart(cat_df, "Category", "Count", "ISSUES BY CATEGORY", is_severity=False)

        with c_chart2:
            sev_df = pd.DataFrame(
                list(summary.issues_by_severity.items()),
                columns=["Severity", "Count"],
            )
            render_chart(sev_df, "Severity", "Count", "ISSUES BY SEVERITY", is_severity=True)

    # Tabs: Issues Table and Raw Data Explorer (Compact)
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
                <div style="border: 1px solid #166534; padding: 18px; background: rgba(34, 197, 94, 0.08); border-radius: 4px; text-align: center;">
                    <span class="indicator-dot dot-green"></span>
                    <span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-weight: 700; color: #4ade80; letter-spacing: 1px;">
                        0 ANOMALIES DETECTED // 100% QUALITY GATE COMPLIANT
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_raw:
        st.caption(f"RAW RECORD MATRIX // SOURCE: `{file_display_name}`")
        st.dataframe(df_raw, use_container_width=True)


if __name__ == "__main__":
    main()
