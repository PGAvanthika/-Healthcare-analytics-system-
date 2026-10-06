# =============================================================================
# app.py — MediSight Phase 1 Entry Point
# =============================================================================
# This file is responsible for:
#   - Configuring the Streamlit page
#   - Loading data (via utils/data_loader.py)
#   - Preprocessing data (via utils/preprocessing.py)
#   - Applying sidebar filters
#   - Calling the KPI engine (via utils/metrics.py)
#   - Rendering the UI
#
# Business logic belongs in utils/. Keep this file focused on layout.
# =============================================================================

import sys
import os

# Ensure the project root is on the Python path so that 'config' and 'utils'
# are importable regardless of the directory Streamlit was launched from.
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd
import numpy as np

from config import (
    APPLICATION_NAME,
    APPLICATION_SUBTITLE,
    DATA_PATH,
    PAGE_TITLE,
    PAGE_ICON,
    LAYOUT,
    COL_DATE,
    COL_DEPT_NAME,
    COL_PATIENT_TYPE,
    COL_GENDER,
    COL_AGE_BUCKET,
    COL_STATUS,
    COL_CITY,
    COL_PATIENT_ID,
    COL_STAFF_ID,
    COL_LOS,
    COL_TREATMENT_COST,
    COL_RATING,
    PROLONGED_STAY_THRESHOLD,
)
from utils.data_loader import load_all_data, get_sheet_names
from utils.preprocessing import (
    preprocess_patient_data,
    preprocess_staff_data,
    preprocess_department_data,
    preprocess_bed_data,
    QualityReport,
)
from utils.metrics import calculate_kpis, KPIResult
from utils.descriptive import (
    plot_patient_type_distribution,
    plot_status_distribution,
    plot_department_distribution,
    plot_monthly_patient_volume,
    plot_age_distribution,
)

# =============================================================================
# Page configuration — must be the first Streamlit call
# =============================================================================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded",
)

# =============================================================================
# Custom CSS — minimal professional styling
# =============================================================================
st.markdown(
    """
    <style>
    /* ---- App background ---- */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* ---- Section headers ---- */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a5276;
        border-bottom: 2px solid #aed6f1;
        padding-bottom: 0.3rem;
        margin-bottom: 0.8rem;
        margin-top: 1.2rem;
    }

    /* ---- KPI card override ---- */
    [data-testid="stMetric"] {
        background-color: #f0f7ff;
        border: 1px solid #d0e8ff;
        border-radius: 8px;
        padding: 0.6rem 1rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #5d6d7e !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        color: #1a5276 !important;
        font-weight: 700 !important;
    }

    /* ---- Sidebar branding ---- */
    .sidebar-brand {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    .sidebar-brand h2 {
        color: #1a5276;
        font-size: 1.6rem;
        margin-bottom: 0;
    }
    .sidebar-brand p {
        font-size: 0.75rem;
        color: #7f8c8d;
        margin-top: 0;
    }

    /* ---- Overview card grid ---- */
    .overview-card {
        background: #f8fbff;
        border: 1px solid #d5e8fb;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
    }
    .overview-label {
        font-size: 0.75rem;
        color: #7f8c8d;
        margin-bottom: 0;
    }
    .overview-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a5276;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Helper utilities
# =============================================================================

def _header(text: str) -> None:
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def _fmt_number(val: float | int, decimals: int = 0) -> str:
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:,.{decimals}f}"


def _fmt_currency(val: float) -> str:
    return f"${val:,.2f}"


# =============================================================================
# Data loading & preprocessing
# =============================================================================

@st.cache_data(show_spinner=False)
def _load_and_preprocess():
    """
    Load raw data and run the full preprocessing pipeline.
    Cached so it only runs once per session (not on every filter change).
    Returns processed DataFrames and the QualityReport.
    """
    raw_patient, raw_staff, raw_dept, raw_bed = load_all_data()
    processed_df, report = preprocess_patient_data(raw_patient, raw_dept)
    staff_df  = preprocess_staff_data(raw_staff)
    dept_df   = preprocess_department_data(raw_dept)
    bed_df    = preprocess_bed_data(raw_bed)
    return processed_df, staff_df, dept_df, bed_df, report


# =============================================================================
# App header
# =============================================================================

col_logo, col_title = st.columns([0.06, 0.94])
with col_logo:
    st.markdown("## 🏥")
with col_title:
    st.markdown(
        f"<h1 style='margin-bottom:0; color:#1a5276;'>{APPLICATION_NAME}</h1>"
        f"<p style='margin-top:0; color:#5d6d7e; font-size:1rem;'>{APPLICATION_SUBTITLE}</p>",
        unsafe_allow_html=True,
    )

st.divider()

# =============================================================================
# Load data — handle errors gracefully
# =============================================================================

try:
    processed_df, staff_df, dept_df, bed_df, quality_report = _load_and_preprocess()
    sheet_names = get_sheet_names()
    load_error = None
except FileNotFoundError as e:
    load_error = str(e)
except Exception as e:
    load_error = f"Unexpected error while loading data: {e}"

if load_error:
    st.error("🚨 **Dataset not found**")
    st.markdown(
        "> Please place `Hospital  Health Care Management Data set.xlsx` "
        "inside the `data/` directory and restart the application."
    )
    st.code(load_error)
    st.stop()

# Validate required columns exist
REQUIRED_COLUMNS = [
    COL_DATE, COL_PATIENT_ID, COL_PATIENT_TYPE, COL_STATUS,
    COL_LOS, COL_TREATMENT_COST, COL_RATING,
]
missing_cols = [c for c in REQUIRED_COLUMNS if c not in processed_df.columns]
if missing_cols:
    st.error("🚨 **Dataset validation failed**")
    st.markdown("The following required columns were not found:")
    for c in missing_cols:
        st.markdown(f"- `{c}`")
    st.stop()


# =============================================================================
# Sidebar — Branding + Filters
# =============================================================================

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        f'<h2>🏥 {APPLICATION_NAME}</h2>'
        f'<p>{APPLICATION_SUBTITLE}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### Filters")

    # ---- Date Range ----
    date_col = processed_df[COL_DATE].dropna()
    min_date = date_col.min().date()
    max_date = date_col.max().date()

    st.markdown("**Date Range**")
    date_from = st.date_input(
        "From",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key="date_from",
    )
    date_to = st.date_input(
        "To",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="date_to",
    )

    st.markdown("---")

    # ---- Department ----
    if COL_DEPT_NAME in processed_df.columns:
        dept_options = sorted(
            processed_df[COL_DEPT_NAME].dropna().unique().tolist()
        )
        selected_depts = st.multiselect(
            "Department",
            options=dept_options,
            default=[],
            placeholder="All departments",
            key="dept_filter",
        )
    else:
        selected_depts = []

    st.markdown("---")

    # ---- Patient Type ----
    patient_type_options = sorted(
        processed_df[COL_PATIENT_TYPE].dropna().unique().tolist()
    )
    selected_types = st.multiselect(
        "Patient Type",
        options=patient_type_options,
        default=[],
        placeholder="All types",
        key="type_filter",
    )

    st.markdown("---")

    # ---- Phase 2+ filters (architecture placeholder) ----
    with st.expander("More filters (coming in Phase 2)", expanded=False):
        st.caption("Gender, Age Group, Status, and City filters will be active in Phase 2.")
        st.multiselect("Gender",    options=[], disabled=True, key="gender_ph")
        st.multiselect("Age Group", options=[], disabled=True, key="age_ph")
        st.multiselect("Status",    options=[], disabled=True, key="status_ph")
        st.multiselect("City",      options=[], disabled=True, key="city_ph")

    st.divider()
    st.caption(f"Dataset: {os.path.basename(DATA_PATH)}")
    st.caption(f"Records loaded: {len(processed_df):,}")


# =============================================================================
# Apply filters
# =============================================================================

filtered_df = processed_df.copy()

# Date range
if COL_DATE in filtered_df.columns:
    filtered_df = filtered_df[
        (filtered_df[COL_DATE].dt.date >= date_from)
        & (filtered_df[COL_DATE].dt.date <= date_to)
    ]

# Department
if selected_depts and COL_DEPT_NAME in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[COL_DEPT_NAME].isin(selected_depts)]

# Patient Type
if selected_types and COL_PATIENT_TYPE in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[COL_PATIENT_TYPE].isin(selected_types)]

# Active filter badge
active_filters = []
if date_from != min_date or date_to != max_date:
    active_filters.append(f"Date: {date_from} → {date_to}")
if selected_depts:
    active_filters.append(f"Dept: {', '.join(selected_depts)}")
if selected_types:
    active_filters.append(f"Type: {', '.join(selected_types)}")

if active_filters:
    st.info(
        "**Active filters:** " + "  |  ".join(active_filters)
        + f"  →  **{len(filtered_df):,} records** of {len(processed_df):,} total"
    )


# =============================================================================
# Calculate KPIs on the filtered DataFrame
# =============================================================================

kpis: KPIResult = calculate_kpis(filtered_df, staff_df, bed_df)


# =============================================================================
# SECTION 1 — Dataset Overview
# =============================================================================

_header("Dataset Overview")

ov1, ov2, ov3, ov4 = st.columns(4)

with ov1:
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Patient Records</p>'
        f'<p class="overview-value">{len(processed_df):,}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Columns</p>'
        f'<p class="overview-value">{len(processed_df.columns)}</p>'
        '</div>',
        unsafe_allow_html=True,
    )

with ov2:
    dr_min = processed_df[COL_DATE].min()
    dr_max = processed_df[COL_DATE].max()
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Date Range</p>'
        f'<p class="overview-value">{dr_min.strftime("%b %d, %Y")}</p>'
        f'<p class="overview-label">to {dr_max.strftime("%b %d, %Y")}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    dept_count = (
        processed_df[COL_DEPT_NAME].nunique()
        if COL_DEPT_NAME in processed_df.columns
        else dept_df["Dpt_ID"].nunique()
    )
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Departments</p>'
        f'<p class="overview-value">{dept_count}</p>'
        '</div>',
        unsafe_allow_html=True,
    )

with ov3:
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Total Staff</p>'
        f'<p class="overview-value">{kpis.total_staff:,}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Bed Records (Bed_Detail)</p>'
        f'<p class="overview-value">{len(bed_df):,}</p>'
        '</div>',
        unsafe_allow_html=True,
    )

with ov4:
    st.markdown(
        '<div class="overview-card">'
        '<p class="overview-label">Excel Sheets Detected</p>'
        f'<p class="overview-value">{len(sheet_names)}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    for sn in sheet_names:
        st.markdown(
            f'<div class="overview-card">'
            f'<p class="overview-label" style="font-size:0.8rem;">📄 {sn}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.divider()

# =============================================================================
# SECTION 2 — Hospital KPIs
# =============================================================================

_header("Hospital KPIs")

if active_filters:
    st.caption(
        f"KPIs reflect **{len(filtered_df):,} filtered records**. "
        "Staff count always shows the full staff roster."
    )

# ---- Row 1 : Patient volume ----
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
r1c1.metric("Total Patients",  _fmt_number(kpis.total_patients))
r1c2.metric("Inpatients",      _fmt_number(kpis.inpatients))
r1c3.metric("Outpatients",     _fmt_number(kpis.outpatients))
r1c4.metric("Total Staff",     _fmt_number(kpis.total_staff))

st.markdown("")

# ---- Row 2 : Operations ----
r2c1, r2c2, r2c3, r2c4 = st.columns(4)
r2c1.metric("Recorded Occupied Beds", _fmt_number(kpis.recorded_occupied_beds))
r2c2.metric("Avg Length of Stay",     f"{kpis.avg_los} days")
r2c3.metric("Avg ER Time",            f"{kpis.avg_er_time} min")
r2c4.metric("Avg Treatment Cost",     _fmt_currency(kpis.avg_treatment_cost))

st.markdown("")

# ---- Row 3 : Revenue & Outcomes ----
r3c1, r3c2, r3c3, r3c4 = st.columns(4)
r3c1.metric("Total Treatment Revenue", _fmt_currency(kpis.total_revenue))
r3c2.metric("Deaths",                  _fmt_number(kpis.deaths))
r3c3.metric("Discharges",              _fmt_number(kpis.discharges))
r3c4.metric("Readmissions",            _fmt_number(kpis.readmissions))

st.markdown("")

# ---- Row 4 : Satisfaction ----
r4c1, _, _, _ = st.columns(4)
r4c1.metric("Avg Patient Rating", f"{kpis.avg_rating} / 5.0")

st.divider()

# =============================================================================
# SECTION 3 — Patient Overview Charts
# =============================================================================
# All five charts receive the same filtered_df used by the KPI engine.
# No independent data loading or filtering takes place here.
# =============================================================================

_header("Patient Overview")

if len(filtered_df) == 0:
    st.warning("No records match the current filters. Adjust the sidebar filters to see charts.")
else:
    # ---- Row 1 : Patient Type  |  Status Distribution ----
    ch1, ch2 = st.columns(2)
    with ch1:
        st.plotly_chart(
            plot_patient_type_distribution(filtered_df),
            use_container_width=True,
        )
    with ch2:
        st.plotly_chart(
            plot_status_distribution(filtered_df),
            use_container_width=True,
        )

    st.markdown("")

    # ---- Row 2 : Department  |  Monthly Volume ----
    ch3, ch4 = st.columns(2)
    with ch3:
        st.plotly_chart(
            plot_department_distribution(filtered_df),
            use_container_width=True,
        )
    with ch4:
        st.plotly_chart(
            plot_monthly_patient_volume(filtered_df),
            use_container_width=True,
        )

    st.markdown("")

    # ---- Row 3 : Age Distribution (half-width, left-aligned) ----
    ch5, _ = st.columns(2)
    with ch5:
        st.plotly_chart(
            plot_age_distribution(filtered_df),
            use_container_width=True,
        )

st.divider()

# =============================================================================
# SECTION 4 — Data Quality
# =============================================================================

_header("Data Quality")

with st.expander("Expand Data Quality Report", expanded=False):

    dq1, dq2 = st.columns(2)

    with dq1:
        st.markdown("**Missing Values by Column**")
        if quality_report.missing_by_column:
            missing_df = pd.DataFrame(
                list(quality_report.missing_by_column.items()),
                columns=["Column", "Missing Count"],
            ).sort_values("Missing Count", ascending=False)
            missing_df["% of Records"] = (
                missing_df["Missing Count"] / quality_report.total_rows_raw * 100
            ).round(1)
            st.dataframe(missing_df, use_container_width=True, hide_index=True)
        else:
            st.success("No missing values detected.")

        st.markdown("**Invalid Numeric Values Coerced to NaN**")
        if quality_report.invalid_numeric:
            inv_df = pd.DataFrame(
                list(quality_report.invalid_numeric.items()),
                columns=["Column", "Count Nulled"],
            )
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
        else:
            st.success("No invalid numeric values detected.")

    with dq2:
        st.markdown("**Summary Statistics**")
        summary_data = {
            "Metric": [
                "Total Raw Records",
                "Duplicate Rows",
                "Invalid Dates (coerced to NaT)",
                "Prolonged Stay Threshold",
            ],
            "Value": [
                f"{quality_report.total_rows_raw:,}",
                f"{quality_report.duplicate_row_count:,}",
                f"{quality_report.invalid_dates:,}",
                f"> {PROLONGED_STAY_THRESHOLD} days",
            ],
        }
        st.dataframe(
            pd.DataFrame(summary_data),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("**Preprocessing Notes**")
        if quality_report.notes:
            for note in quality_report.notes:
                st.markdown(f"- {note}")
        else:
            st.info("No preprocessing actions were taken.")

    st.divider()

    st.markdown("**Column Summary (processed dataset)**")
    # Show column summary without any PII (Name column excluded)
    EXCLUDE_PII = ["Name"]
    summary_cols = [c for c in processed_df.columns if c not in EXCLUDE_PII]
    col_summary = pd.DataFrame({
        "Column": summary_cols,
        "Dtype": [str(processed_df[c].dtype) for c in summary_cols],
        "Non-Null": [int(processed_df[c].notna().sum()) for c in summary_cols],
        "Null": [int(processed_df[c].isna().sum()) for c in summary_cols],
        "Unique Values": [int(processed_df[c].nunique()) for c in summary_cols],
    })
    st.dataframe(col_summary, use_container_width=True, hide_index=True)


# =============================================================================
# Footer
# =============================================================================

st.markdown("")
st.caption(
    f"MediSight Phase 1 · Data sourced from: `{DATA_PATH}` · "
    "No data was generated, modified, or written back to the source file."
)
