# =============================================================================
# app.py — MediSight  |  Phase 1
# =============================================================================
# Single-file app with radio-button navigation in the sidebar.
# Using one file keeps all three "pages" sharing the same:
#   - cached DataFrames
#   - sidebar filters
#   - filtered_df  →  KPI engine  →  charts
#
# Responsibilities:
#   - Page config & global CSS
#   - Data load + preprocessing  (via utils/)
#   - Sidebar: branding, navigation, filters, data-source info
#   - Filter application  →  filtered_df
#   - KPI calculation  (via utils/metrics.py)
#   - Route to the correct page renderer
#   - Page renderers: Dataset Overview / Hospital KPIs / Patient Overview
#                     + Coming-Soon placeholders
# =============================================================================

import sys
import os

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd

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
from utils.diagnostic import (
    # Derived category columns
    add_derived_diagnostic_cols,
    compute_er_thresholds,
    compute_los_thresholds,
    compute_cost_thresholds,
    # Module A — Readmission
    readmission_summary,
    readmission_breakdown_table,
    plot_readmission_by_department,
    plot_readmission_by_patient_type,
    plot_readmission_by_age_bucket,
    plot_readmission_by_category,
    # Module B — ER Wait-Time
    er_summary_stats,
    plot_er_distribution,
    plot_er_by_department,
    plot_er_wait_category_dist,
    plot_er_vs_los_scatter,
    # Module C — LOS vs Department
    los_by_department_stats,
    plot_avg_los_by_department,
    plot_los_box_by_department,
    plot_los_vs_cost,
    # Module D — Cost Analysis
    cost_by_department_stats,
    plot_cost_histogram,
    plot_cost_box_by_department,
    plot_avg_cost_by_department,
    plot_total_revenue_by_department,
    DIAGNOSIS_AVAILABLE,
    DIAGNOSIS_NOTE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens  (single source of truth for the healthcare colour palette)
# ─────────────────────────────────────────────────────────────────────────────
C_BG        = "#F5F8FA"   # page background
C_CARD      = "#FFFFFF"   # card / metric background
C_PRIMARY   = "#123B5D"   # headers, metric values
C_TEAL      = "#0F766E"   # accent bars / icons
C_ACCENT    = "#2A9D8F"   # hover / line colour
C_TEXT      = "#17324D"   # body text
C_SUBTEXT   = "#64748B"   # labels, captions
C_BORDER    = "#D9E2EC"   # card borders, dividers
C_ACTIVE_BG = "#E8F4F8"   # nav item active background

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Page & block ─────────────────────────────────────────── */
.stApp {{
    background-color: {C_BG};
}}
.block-container {{
    padding-top: 1.8rem;
    padding-bottom: 2.5rem;
    max-width: 1280px;
}}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: {C_CARD};
    border-right: 1px solid {C_BORDER};
}}
[data-testid="stSidebar"] * {{
    color: {C_TEXT} !important;
}}

/* ── Radio nav — make it look like a menu ─────────────────── */
[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    display: block;
    padding: 0.45rem 0.75rem;
    border-radius: 6px;
    font-size: 0.88rem;
    font-weight: 500;
    color: {C_TEXT} !important;
    cursor: pointer;
    transition: background 0.15s;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background-color: {C_ACTIVE_BG};
}}
/* hide the actual radio dot */
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {{
    margin: 0;
}}
div[role="radiogroup"] > label > div:first-child {{
    display: none !important;
}}

/* ── KPI metric cards ─────────────────────────────────────── */
[data-testid="stMetric"] {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
[data-testid="stMetricLabel"] > div {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: {C_SUBTEXT} !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
[data-testid="stMetricValue"] > div {{
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: {C_PRIMARY} !important;
}}

/* ── Overview stat cards ──────────────────────────────────── */
.stat-card {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.stat-label {{
    font-size: 0.75rem;
    font-weight: 600;
    color: {C_SUBTEXT};
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 0.25rem 0;
}}
.stat-value {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {C_PRIMARY};
    margin: 0;
}}
.stat-sub {{
    font-size: 0.78rem;
    color: {C_SUBTEXT};
    margin: 0.15rem 0 0 0;
}}

/* ── Sheet / column badge ─────────────────────────────────── */
.sheet-badge {{
    display: inline-block;
    background: {C_ACTIVE_BG};
    border: 1px solid {C_BORDER};
    border-radius: 5px;
    padding: 0.2rem 0.6rem;
    font-size: 0.78rem;
    color: {C_PRIMARY};
    margin: 0.2rem 0.2rem 0 0;
    font-weight: 500;
}}

/* ── Page header ──────────────────────────────────────────── */
.page-header {{
    border-bottom: 2px solid {C_BORDER};
    padding-bottom: 0.6rem;
    margin-bottom: 1.4rem;
}}
.page-header h2 {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {C_PRIMARY};
    margin: 0 0 0.1rem 0;
}}
.page-header p {{
    font-size: 0.85rem;
    color: {C_SUBTEXT};
    margin: 0;
}}

/* ── Section sub-header ───────────────────────────────────── */
.section-header {{
    font-size: 0.82rem;
    font-weight: 700;
    color: {C_SUBTEXT};
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 1.6rem 0 0.7rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid {C_BORDER};
}}

/* ── Filter info banner ───────────────────────────────────── */
[data-testid="stInfo"] {{
    background-color: #EAF6FB !important;
    border-left: 3px solid {C_ACCENT} !important;
    border-radius: 6px !important;
    color: {C_TEXT} !important;
}}

/* ── Coming-soon card ─────────────────────────────────────── */
.coming-soon-card {{
    background: {C_CARD};
    border: 1px dashed {C_BORDER};
    border-radius: 12px;
    padding: 3rem 2rem;
    text-align: center;
}}
.coming-soon-icon {{
    font-size: 2.8rem;
    margin-bottom: 0.6rem;
}}
.coming-soon-title {{
    font-size: 1.2rem;
    font-weight: 700;
    color: {C_PRIMARY};
    margin: 0 0 0.4rem 0;
}}
.coming-soon-sub {{
    font-size: 0.9rem;
    color: {C_SUBTEXT};
    margin: 0;
}}

/* ── Dataframes / tables ──────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}

/* ── Sidebar filter section label ─────────────────────────── */
.filter-section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    color: {C_SUBTEXT};
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 1rem 0 0.4rem 0;
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val: float | int, decimals: int = 0) -> str:
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:,.{decimals}f}"

def _fmt_usd(val: float) -> str:
    return f"${val:,.2f}"

def _page_header(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-header">'
        f'<h2>{icon}&nbsp; {title}</h2>'
        f'<p>{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

def _section(text: str) -> None:
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

def _stat_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<p class="stat-sub">{sub}</p>' if sub else ""
    return (
        f'<div class="stat-card">'
        f'<p class="stat-label">{label}</p>'
        f'<p class="stat-value">{value}</p>'
        f'{sub_html}'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data loading  (cached — runs once per session)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_and_preprocess():
    raw_patient, raw_staff, raw_dept, raw_bed = load_all_data()
    processed_df, report = preprocess_patient_data(raw_patient, raw_dept)
    staff_df = preprocess_staff_data(raw_staff)
    dept_df  = preprocess_department_data(raw_dept)
    bed_df   = preprocess_bed_data(raw_bed)
    return processed_df, staff_df, dept_df, bed_df, report


# ─────────────────────────────────────────────────────────────────────────────
# Load data & handle errors before rendering anything else
# ─────────────────────────────────────────────────────────────────────────────

try:
    processed_df, staff_df, dept_df, bed_df, quality_report = _load_and_preprocess()
    sheet_names = get_sheet_names()
    load_error  = None
except FileNotFoundError as exc:
    load_error = str(exc)
except Exception as exc:
    load_error = f"Unexpected error while loading data: {exc}"

if load_error:
    st.error("🚨 **Dataset not found**")
    st.markdown(
        "> Place `Hospital  Health Care Management Data set.xlsx` "
        "inside the `data/` directory and restart the app."
    )
    st.code(load_error)
    st.stop()

REQUIRED_COLUMNS = [
    COL_DATE, COL_PATIENT_ID, COL_PATIENT_TYPE, COL_STATUS,
    COL_LOS, COL_TREATMENT_COST, COL_RATING,
]
missing_cols = [c for c in REQUIRED_COLUMNS if c not in processed_df.columns]
if missing_cols:
    st.error("🚨 **Dataset validation failed** — missing columns:")
    for c in missing_cols:
        st.markdown(f"- `{c}`")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — branding · navigation · filters · data source
# ─────────────────────────────────────────────────────────────────────────────

NAV_ITEMS = [
    "📋  Dataset Overview",
    "📊  Hospital KPIs",
    "🩺  Patient Overview",
    "🔬  Diagnostic Analytics",
    "🤖  Predictive Analytics",
]

with st.sidebar:
    # ── Brand ──────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="text-align:center; padding: 1.2rem 0 0.8rem 0;">
            <div style="font-size:2rem;">🏥</div>
            <div style="font-size:1.25rem; font-weight:800;
                        color:{C_PRIMARY}; line-height:1.2;">
                {APPLICATION_NAME}
            </div>
            <div style="font-size:0.68rem; color:{C_SUBTEXT};
                        margin-top:0.2rem; line-height:1.3;">
                {APPLICATION_SUBTITLE}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f'<hr style="border:none; border-top:1px solid {C_BORDER}; margin:0.5rem 0;">', unsafe_allow_html=True)

    # ── Navigation ─────────────────────────────────────────────
    st.markdown('<p class="filter-section-label">Navigation</p>', unsafe_allow_html=True)
    selected_page = st.radio(
        label="nav",
        options=NAV_ITEMS,
        index=0,
        label_visibility="collapsed",
        key="nav_radio",
    )

    st.markdown(f'<hr style="border:none; border-top:1px solid {C_BORDER}; margin:0.6rem 0;">', unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────
    st.markdown('<p class="filter-section-label">Filters</p>', unsafe_allow_html=True)

    # Date Range
    date_series = processed_df[COL_DATE].dropna()
    min_date    = date_series.min().date()
    max_date    = date_series.max().date()

    date_from = st.date_input(
        "From",
        value=min_date, min_value=min_date, max_value=max_date,
        key="date_from",
    )
    date_to = st.date_input(
        "To",
        value=max_date, min_value=min_date, max_value=max_date,
        key="date_to",
    )

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    # Department
    if COL_DEPT_NAME in processed_df.columns:
        dept_options   = sorted(processed_df[COL_DEPT_NAME].dropna().unique().tolist())
        selected_depts = st.multiselect(
            "Department",
            options=dept_options, default=[],
            placeholder="All departments",
            key="dept_filter",
        )
    else:
        selected_depts = []

    # Patient Type
    type_options   = sorted(processed_df[COL_PATIENT_TYPE].dropna().unique().tolist())
    selected_types = st.multiselect(
        "Patient Type",
        options=type_options, default=[],
        placeholder="All types",
        key="type_filter",
    )

    # Phase 2+ placeholders
    with st.expander("More filters — Phase 2", expanded=False):
        st.caption("Gender, Age Group, Status, City — coming in Phase 2.")
        st.multiselect("Gender",    options=[], disabled=True, key="gender_ph")
        st.multiselect("Age Group", options=[], disabled=True, key="age_ph")
        st.multiselect("Status",    options=[], disabled=True, key="status_ph")
        st.multiselect("City",      options=[], disabled=True, key="city_ph")

    st.markdown(f'<hr style="border:none; border-top:1px solid {C_BORDER}; margin:0.8rem 0;">', unsafe_allow_html=True)

    # ── Data source ────────────────────────────────────────────
    st.markdown('<p class="filter-section-label">Data Source</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.73rem; color:{C_SUBTEXT}; line-height:1.6;">'
        f'📁 {os.path.basename(DATA_PATH)}<br>'
        f'🗂 {len(sheet_names)} sheets detected<br>'
        f'👤 {len(processed_df):,} patient records'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Apply filters  →  filtered_df  (shared by KPIs and all charts)
# ─────────────────────────────────────────────────────────────────────────────

filtered_df = processed_df.copy()

if COL_DATE in filtered_df.columns:
    filtered_df = filtered_df[
        (filtered_df[COL_DATE].dt.date >= date_from) &
        (filtered_df[COL_DATE].dt.date <= date_to)
    ]

if selected_depts and COL_DEPT_NAME in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[COL_DEPT_NAME].isin(selected_depts)]

if selected_types and COL_PATIENT_TYPE in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[COL_PATIENT_TYPE].isin(selected_types)]

# Build active-filter description for banners
active_filters: list[str] = []
if date_from != min_date or date_to != max_date:
    active_filters.append(f"Date: {date_from} → {date_to}")
if selected_depts:
    active_filters.append(f"Dept: {', '.join(selected_depts)}")
if selected_types:
    active_filters.append(f"Type: {', '.join(selected_types)}")


# ─────────────────────────────────────────────────────────────────────────────
# KPIs  (calculated once; shared across any page that needs them)
# ─────────────────────────────────────────────────────────────────────────────

kpis: KPIResult = calculate_kpis(filtered_df, staff_df, bed_df)


# ─────────────────────────────────────────────────────────────────────────────
# App-level header  (always visible above the page content)
# ─────────────────────────────────────────────────────────────────────────────

hdr_left, hdr_right = st.columns([0.75, 0.25])
with hdr_left:
    st.markdown(
        f'<h1 style="margin:0; font-size:1.6rem; font-weight:800; color:{C_PRIMARY};">'
        f'🏥&nbsp; {APPLICATION_NAME}</h1>'
        f'<p style="margin:0.1rem 0 0 0; font-size:0.88rem; color:{C_SUBTEXT};">'
        f'{APPLICATION_SUBTITLE}</p>',
        unsafe_allow_html=True,
    )
with hdr_right:
    if active_filters:
        total  = len(processed_df)
        subset = len(filtered_df)
        pct    = round(subset / total * 100, 1) if total else 0
        st.markdown(
            f'<div style="text-align:right; margin-top:0.3rem;">'
            f'<span style="background:{C_ACTIVE_BG}; border:1px solid {C_BORDER}; '
            f'border-radius:20px; padding:0.25rem 0.75rem; font-size:0.75rem; '
            f'color:{C_PRIMARY}; font-weight:600;">'
            f'🔽 {subset:,} / {total:,} records ({pct}%)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown(f'<hr style="border:none; border-top:1px solid {C_BORDER}; margin:0.8rem 0 1.2rem 0;">', unsafe_allow_html=True)

# Show filter pill strip when any filter is active
if active_filters:
    pills = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(
        f'<span style="color:{C_TEAL}; font-weight:600;">{f}</span>'
        for f in active_filters
    )
    st.markdown(
        f'<div style="background:{C_ACTIVE_BG}; border:1px solid {C_BORDER}; '
        f'border-radius:6px; padding:0.4rem 0.8rem; font-size:0.8rem; '
        f'color:{C_TEXT}; margin-bottom:1rem;">'
        f'Active filters:&nbsp;&nbsp;{pills}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE RENDERERS
# ═════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — Dataset Overview
# ─────────────────────────────────────────────────────────────────────────────

def render_dataset_overview():
    _page_header("📋", "Dataset Overview", "Source workbook structure, record counts, and data quality.")

    # ── Row 1: top-line stats ─────────────────────────────────
    _section("Dataset Statistics")
    c1, c2, c3, c4 = st.columns(4)

    dr_min = processed_df[COL_DATE].min()
    dr_max = processed_df[COL_DATE].max()
    dept_count = (
        processed_df[COL_DEPT_NAME].nunique()
        if COL_DEPT_NAME in processed_df.columns
        else dept_df["Dpt_ID"].nunique()
    )

    with c1:
        st.markdown(_stat_card("Patient Records",  f"{len(processed_df):,}",
                               "rows in Detail data dataset"), unsafe_allow_html=True)
        st.markdown(_stat_card("Columns",          str(len(processed_df.columns)),
                               "in processed DataFrame"), unsafe_allow_html=True)
    with c2:
        st.markdown(_stat_card("Date Range",
                               dr_min.strftime("%b %d, %Y"),
                               f"to {dr_max.strftime('%b %d, %Y')}"), unsafe_allow_html=True)
        st.markdown(_stat_card("Departments", str(dept_count),
                               "unique departments"), unsafe_allow_html=True)
    with c3:
        st.markdown(_stat_card("Total Staff",      f"{kpis.total_staff:,}",
                               "unique staff members"), unsafe_allow_html=True)
        st.markdown(_stat_card("Bed Records",      f"{len(bed_df):,}",
                               "rows in Bed_Detail"), unsafe_allow_html=True)
    with c4:
        st.markdown(_stat_card("Excel Sheets",     str(len(sheet_names)),
                               "sheets detected"), unsafe_allow_html=True)
        st.markdown(_stat_card("Staff Records",    f"{len(staff_df):,}",
                               "rows in Staff_Detail"), unsafe_allow_html=True)

    # ── Sheet names ───────────────────────────────────────────
    _section("Workbook Sheets")
    badges = "".join(f'<span class="sheet-badge">📄 {s}</span>' for s in sheet_names)
    st.markdown(badges, unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

    # ── Data Quality ──────────────────────────────────────────
    _section("Data Quality")

    with st.expander("Missing Values & Preprocessing Report", expanded=True):
        dq1, dq2 = st.columns(2)

        with dq1:
            st.markdown(
                f'<p style="font-size:0.82rem; font-weight:600; color:{C_TEXT}; margin-bottom:0.4rem;">'
                f'Missing Values by Column</p>',
                unsafe_allow_html=True,
            )
            if quality_report.missing_by_column:
                mv_df = (
                    pd.DataFrame(
                        list(quality_report.missing_by_column.items()),
                        columns=["Column", "Missing"],
                    )
                    .sort_values("Missing", ascending=False)
                )
                mv_df["% of Total"] = (mv_df["Missing"] / quality_report.total_rows_raw * 100).round(1)
                st.dataframe(mv_df, use_container_width=True, hide_index=True)
            else:
                st.success("No missing values detected.")

            st.markdown(
                f'<p style="font-size:0.82rem; font-weight:600; color:{C_TEXT}; margin:0.8rem 0 0.4rem 0;">'
                f'Invalid Numerics Coerced to NaN</p>',
                unsafe_allow_html=True,
            )
            if quality_report.invalid_numeric:
                inv_df = pd.DataFrame(
                    list(quality_report.invalid_numeric.items()),
                    columns=["Column", "Count Nulled"],
                )
                st.dataframe(inv_df, use_container_width=True, hide_index=True)
            else:
                st.success("No invalid numeric values detected.")

        with dq2:
            st.markdown(
                f'<p style="font-size:0.82rem; font-weight:600; color:{C_TEXT}; margin-bottom:0.4rem;">'
                f'Summary</p>',
                unsafe_allow_html=True,
            )
            summary = pd.DataFrame({
                "Metric": [
                    "Total Raw Records",
                    "Duplicate Rows",
                    "Invalid Dates (→ NaT)",
                    "Prolonged Stay Threshold",
                ],
                "Value": [
                    f"{quality_report.total_rows_raw:,}",
                    f"{quality_report.duplicate_row_count:,}",
                    f"{quality_report.invalid_dates:,}",
                    f"> {PROLONGED_STAY_THRESHOLD} days",
                ],
            })
            st.dataframe(summary, use_container_width=True, hide_index=True)

            st.markdown(
                f'<p style="font-size:0.82rem; font-weight:600; color:{C_TEXT}; margin:0.8rem 0 0.4rem 0;">'
                f'Preprocessing Notes</p>',
                unsafe_allow_html=True,
            )
            if quality_report.notes:
                for note in quality_report.notes:
                    st.markdown(
                        f'<p style="font-size:0.8rem; color:{C_SUBTEXT}; margin:0.15rem 0;">• {note}</p>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No preprocessing actions were required.")

    # ── Column summary ────────────────────────────────────────
    with st.expander("Column Summary (processed DataFrame)", expanded=False):
        EXCLUDE_PII = ["Name"]
        cols_show   = [c for c in processed_df.columns if c not in EXCLUDE_PII]
        col_df = pd.DataFrame({
            "Column":        cols_show,
            "Dtype":         [str(processed_df[c].dtype) for c in cols_show],
            "Non-Null":      [int(processed_df[c].notna().sum()) for c in cols_show],
            "Null":          [int(processed_df[c].isna().sum())  for c in cols_show],
            "Unique Values": [int(processed_df[c].nunique())     for c in cols_show],
        })
        st.dataframe(col_df, use_container_width=True, hide_index=True)

    # ── Footer note ───────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.75rem; color:{C_SUBTEXT}; margin-top:1.5rem;">'
        f'Data sourced from <code>{DATA_PATH}</code>. '
        f'Original file is never modified.</p>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — Hospital KPIs
# ─────────────────────────────────────────────────────────────────────────────

def render_hospital_kpis():
    _page_header("📊", "Hospital KPIs",
                 f"13 key performance indicators · {len(filtered_df):,} records in view")

    if active_filters:
        st.info(
            f"**Filtered view** — {len(filtered_df):,} of {len(processed_df):,} records. "
            "Staff count always reflects the full roster."
        )

    # ── Row 1 : Patient Volume ────────────────────────────────
    _section("Patient Volume")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Patients",  _fmt(kpis.total_patients))
    k2.metric("Inpatients",      _fmt(kpis.inpatients))
    k3.metric("Outpatients",     _fmt(kpis.outpatients))
    k4.metric("Total Staff",     _fmt(kpis.total_staff))

    # ── Row 2 : Operational ───────────────────────────────────
    _section("Operational")
    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Recorded Occupied Beds", _fmt(kpis.recorded_occupied_beds))
    k6.metric("Avg Length of Stay",     f"{kpis.avg_los} days")
    k7.metric("Avg ER Time",            f"{kpis.avg_er_time} min")
    k8.metric("Avg Treatment Cost",     _fmt_usd(kpis.avg_treatment_cost))

    # ── Row 3 : Revenue & Outcomes ────────────────────────────
    _section("Revenue & Outcomes")
    k9, k10, k11, k12 = st.columns(4)
    k9.metric("Total Treatment Revenue", _fmt_usd(kpis.total_revenue))
    k10.metric("Deaths",                 _fmt(kpis.deaths))
    k11.metric("Discharges",             _fmt(kpis.discharges))
    k12.metric("Readmissions",           _fmt(kpis.readmissions))

    # ── Row 4 : Satisfaction ──────────────────────────────────
    _section("Patient Satisfaction")
    k13, _, _, _ = st.columns(4)
    k13.metric("Avg Patient Rating", f"{kpis.avg_rating} / 5.0")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — Patient Overview (charts)
# ─────────────────────────────────────────────────────────────────────────────

def render_patient_overview():
    _page_header("🩺", "Patient Overview",
                 f"5 interactive charts · {len(filtered_df):,} records in view")

    if len(filtered_df) == 0:
        st.warning("No records match the current filters. Adjust the sidebar to see charts.")
        return

    if active_filters:
        st.info(
            f"Charts reflect **{len(filtered_df):,} filtered records** "
            f"({len(processed_df):,} total)."
        )

    # ── Row 1 : Donut + Status Bar ────────────────────────────
    _section("Distribution")
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

    # ── Row 2 : Department + Monthly Volume ───────────────────
    _section("Volume")
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

    # ── Row 3 : Age Distribution ──────────────────────────────
    _section("Demographics")
    ch5, spacer = st.columns(2)
    with ch5:
        st.plotly_chart(
            plot_age_distribution(filtered_df),
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — Diagnostic Analytics  (Phase 2)
# ─────────────────────────────────────────────────────────────────────────────

def render_diagnostic_analytics():
    _page_header(
        "🔬", "Diagnostic Analytics",
        f"Phase 2 · {len(filtered_df):,} records in view · "
        "All analyses respond to the sidebar filters",
    )

    if len(filtered_df) == 0:
        st.warning("No records match the current filters. Adjust the sidebar to see analyses.")
        return

    if active_filters:
        st.info(
            f"**Filtered view** — analyses reflect **{len(filtered_df):,}** of "
            f"{len(processed_df):,} total records."
        )

    # Add derived category columns — thresholds computed from filtered_df
    diag_df = add_derived_diagnostic_cols(filtered_df)

    # Pre-compute threshold labels for section sub-headings
    er_low,   er_high   = compute_er_thresholds(filtered_df)
    los_low,  los_high  = compute_los_thresholds(filtered_df)
    cost_low, cost_high = compute_cost_thresholds(filtered_df)

    # ═══════════════════════════════════════════════════════════
    # SECTION A — Readmission Analysis
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="background:{C_PRIMARY}; color:#FFFFFF; border-radius:8px; '
        f'padding:0.55rem 1rem; font-size:0.82rem; font-weight:700; '
        f'letter-spacing:0.06em; margin:1.4rem 0 0.9rem 0;">'
        f'A &nbsp;·&nbsp; READMISSION ANALYSIS'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Readmission patterns are presented as associated factors — not proven causes. "
        "Readmission_Flag = 1 where Status = 'Readmit'."
    )

    rsumm = readmission_summary(diag_df)

    # Top-line readmission KPIs
    ra1, ra2, ra3, ra4 = st.columns(4)
    ra1.metric("Total Patients",       _fmt(rsumm["total_patients"]))
    ra2.metric("Readmitted Patients",  _fmt(rsumm["readmitted"]))
    ra3.metric("Readmission Rate",     f"{rsumm['readmission_rate_pct']}%")
    ra4.metric("Not Readmitted",
               _fmt(rsumm["total_patients"] - rsumm["readmitted"]))

    st.markdown("")

    # Row 1 — By Department + By Patient Type
    _section("Readmission Rate by Department & Patient Type")
    rc1, rc2 = st.columns(2)
    with rc1:
        st.plotly_chart(plot_readmission_by_department(diag_df),
                        use_container_width=True)
    with rc2:
        st.plotly_chart(plot_readmission_by_patient_type(diag_df),
                        use_container_width=True)

    st.markdown("")

    # Row 2 — By Age Group + By ER Wait Category
    _section("Readmission Rate by Age Group & ER Wait Category")
    rc3, rc4 = st.columns(2)
    with rc3:
        st.plotly_chart(plot_readmission_by_age_bucket(diag_df),
                        use_container_width=True)
    with rc4:
        st.plotly_chart(
            plot_readmission_by_category(
                diag_df, "ER_Wait_Category",
                f"Readmission Rate by ER Wait Category "
                f"(Short ≤{er_low:.0f} min · Long >{er_high:.0f} min)",
            ),
            use_container_width=True,
        )

    st.markdown("")

    # Row 3 — By LOS Category + By Cost Category
    _section("Readmission Rate by LOS Category & Cost Category")
    rc5, rc6 = st.columns(2)
    with rc5:
        st.plotly_chart(
            plot_readmission_by_category(
                diag_df, "LOS_Category",
                f"Readmission Rate by LOS Category "
                f"(Short ≤{los_low:.0f}d · Prolonged >{los_high:.0f}d)",
            ),
            use_container_width=True,
        )
    with rc6:
        st.plotly_chart(
            plot_readmission_by_category(
                diag_df, "Cost_Category",
                f"Readmission Rate by Cost Category "
                f"(Low ≤${cost_low:,.0f} · High >${cost_high:,.0f})",
            ),
            use_container_width=True,
        )

    # Full breakdown table
    with st.expander("Full Readmission Breakdown Table", expanded=False):
        st.caption(
            "Readmission Rate = Readmitted / Total within each group. "
            "Rates above 20% are highlighted."
        )
        breakdown = readmission_breakdown_table(diag_df)
        if not breakdown.empty:
            breakdown = breakdown.rename(columns={"Rate_%": "Rate (%)"})
            st.dataframe(
                breakdown.style.apply(
                    lambda row: [
                        f"background-color: #FEF2F2; color: {C_TEXT};"
                        if row["Rate (%)"] >= 20 else "" for _ in row
                    ],
                    axis=1,
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No breakdown data available for current filter.")

    # ═══════════════════════════════════════════════════════════
    # SECTION B — ER Wait-Time Analysis
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="background:{C_TEAL}; color:#FFFFFF; border-radius:8px; '
        f'padding:0.55rem 1rem; font-size:0.82rem; font-weight:700; '
        f'letter-spacing:0.06em; margin:2rem 0 0.9rem 0;">'
        f'B &nbsp;·&nbsp; ER WAIT-TIME ANALYSIS'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "ER_Time is available for 1,787 of 2,506 records in the full dataset "
        "(719 records — mostly Inpatients — have no ER time recorded)."
    )

    er_stats = er_summary_stats(diag_df)
    if er_stats:
        eb1, eb2, eb3, eb4, eb5 = st.columns(5)
        eb1.metric("Patients with ER Data", _fmt(er_stats["count"]))
        eb2.metric("Mean ER Time",          f"{er_stats['mean']} min")
        eb3.metric("Median ER Time",        f"{er_stats['median']} min")
        eb4.metric("Min / Max",
                   f"{er_stats['min']:.0f} / {er_stats['max']:.0f} min")
        eb5.metric("Std Dev",               f"{er_stats['std']} min")

        st.markdown("")

        # Row 1 — Distribution + Category donut
        _section("ER Time Distribution & Category Breakdown")
        eb_c1, eb_c2 = st.columns(2)
        with eb_c1:
            st.plotly_chart(plot_er_distribution(diag_df),
                            use_container_width=True)
        with eb_c2:
            st.plotly_chart(plot_er_wait_category_dist(diag_df),
                            use_container_width=True)

        st.markdown("")

        # Row 2 — By Department + ER vs LOS scatter
        _section("ER Time by Department & Relationship with LOS")
        eb_c3, eb_c4 = st.columns(2)
        with eb_c3:
            st.plotly_chart(plot_er_by_department(diag_df),
                            use_container_width=True)
        with eb_c4:
            st.plotly_chart(plot_er_vs_los_scatter(diag_df),
                            use_container_width=True)

        # Percentile reference
        with st.expander("ER Time Percentile Reference", expanded=False):
            perc_df = pd.DataFrame({
                "Percentile": ["P10", "P25 (Q1)", "P50 (Median)",
                               "P75 (Q3)", "P90",
                               f"Category: Short (≤{er_low:.0f} min)",
                               f"Category: Moderate ({er_low:.0f}–{er_high:.0f} min)",
                               f"Category: Long (>{er_high:.0f} min)"],
                "Value": [
                    f"{er_stats['p25']} min",
                    f"{er_stats['p25']} min",
                    f"{er_stats['median']} min",
                    f"{er_stats['p75']} min",
                    f"{er_stats['p90']} min",
                    f"≤ {er_low:.0f} min  (≤ Q33 of this view)",
                    f"{er_low:.0f} – {er_high:.0f} min  (Q33–Q66)",
                    f"> {er_high:.0f} min  (> Q66)",
                ],
            })
            st.dataframe(perc_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No ER_Time data available for the current filter selection.")

    # ═══════════════════════════════════════════════════════════
    # SECTION C — LOS vs Department
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="background:{C_ACCENT}; color:#FFFFFF; border-radius:8px; '
        f'padding:0.55rem 1rem; font-size:0.82rem; font-weight:700; '
        f'letter-spacing:0.06em; margin:2rem 0 0.9rem 0;">'
        f'C &nbsp;·&nbsp; LENGTH OF STAY vs DEPARTMENT'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Department is a categorical variable — a Pearson correlation between "
        "department names and LOS values is not statistically appropriate. "
        "Per-department group statistics are used instead. "
        "A numeric Pearson r is shown only for LOS vs Treatment Cost (both numeric)."
    )

    # Row 1 — Avg LOS bar + LOS box
    _section("Average LOS & Distribution by Department")
    lc1, lc2 = st.columns(2)
    with lc1:
        st.plotly_chart(plot_avg_los_by_department(diag_df),
                        use_container_width=True)
    with lc2:
        st.plotly_chart(plot_los_box_by_department(diag_df),
                        use_container_width=True)

    st.markdown("")

    # Row 2 — LOS vs cost scatter (full width)
    _section("LOS vs Treatment Cost (Numeric Correlation)")
    lc3, _ = st.columns([0.7, 0.3])
    with lc3:
        st.plotly_chart(plot_los_vs_cost(diag_df), use_container_width=True)

    # Department stats table
    with st.expander("LOS Statistics by Department", expanded=False):
        los_stats = los_by_department_stats(diag_df)
        if not los_stats.empty:
            st.dataframe(los_stats, use_container_width=True, hide_index=True)
        else:
            st.info("No LOS department data available for current filter.")

    # ═══════════════════════════════════════════════════════════
    # SECTION D — Treatment Cost Analysis
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="background:#475569; color:#FFFFFF; border-radius:8px; '
        f'padding:0.55rem 1rem; font-size:0.82rem; font-weight:700; '
        f'letter-spacing:0.06em; margin:2rem 0 0.9rem 0;">'
        f'D &nbsp;·&nbsp; TREATMENT COST ANALYSIS'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Diagnosis availability notice — honest and prominent
    st.info(DIAGNOSIS_NOTE)

    # Top-line cost KPIs
    cost_valid = diag_df[COL_TREATMENT_COST].dropna()
    dc1, dc2, dc3, dc4 = st.columns(4)
    dc1.metric("Total Revenue",    _fmt_usd(float(cost_valid.sum())))
    dc2.metric("Avg Cost/Patient", _fmt_usd(float(cost_valid.mean())))
    dc3.metric("Median Cost",      _fmt_usd(float(cost_valid.median())))
    dc4.metric("Cost Range",
               f"${cost_valid.min():,.2f} – ${cost_valid.max():,.2f}")

    st.markdown("")

    # Row 1 — Cost histogram + box by department
    _section("Cost Distribution")
    dc_c1, dc_c2 = st.columns(2)
    with dc_c1:
        st.plotly_chart(plot_cost_histogram(diag_df),
                        use_container_width=True)
    with dc_c2:
        st.plotly_chart(plot_cost_box_by_department(diag_df),
                        use_container_width=True)

    st.markdown("")

    # Row 2 — Avg cost + Total revenue by department
    _section("Average Cost & Total Revenue by Department")
    dc_c3, dc_c4 = st.columns(2)
    with dc_c3:
        st.plotly_chart(plot_avg_cost_by_department(diag_df),
                        use_container_width=True)
    with dc_c4:
        st.plotly_chart(plot_total_revenue_by_department(diag_df),
                        use_container_width=True)

    # Full stats table
    with st.expander("Treatment Cost Statistics by Department", expanded=False):
        cost_stats = cost_by_department_stats(diag_df)
        if not cost_stats.empty:
            st.dataframe(cost_stats, use_container_width=True, hide_index=True)
        else:
            st.info("No cost data available for current filter.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — Coming Soon helper  (Predictive Analytics)
# ─────────────────────────────────────────────────────────────────────────────

def render_coming_soon(title: str, icon: str, phase: str, features: list[str]):
    _page_header(icon, title, f"Coming in {phase}")
    st.markdown(
        f'<div class="coming-soon-card">'
        f'<div class="coming-soon-icon">{icon}</div>'
        f'<p class="coming-soon-title">{title} — Coming Soon</p>'
        f'<p class="coming-soon-sub">This module will be implemented in {phase}.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    _section("Planned Features")
    cols = st.columns(2)
    for i, feat in enumerate(features):
        with cols[i % 2]:
            st.markdown(
                f'<div style="background:{C_CARD}; border:1px solid {C_BORDER}; '
                f'border-radius:8px; padding:0.7rem 1rem; margin-bottom:0.5rem; '
                f'font-size:0.84rem; color:{C_TEXT};">'
                f'🔹 {feat}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Router — show the selected page
# ─────────────────────────────────────────────────────────────────────────────

if selected_page == NAV_ITEMS[0]:
    render_dataset_overview()

elif selected_page == NAV_ITEMS[1]:
    render_hospital_kpis()

elif selected_page == NAV_ITEMS[2]:
    render_patient_overview()

elif selected_page == NAV_ITEMS[3]:
    render_diagnostic_analytics()

elif selected_page == NAV_ITEMS[4]:
    render_coming_soon(
        title="Predictive Analytics",
        icon="🤖",
        phase="Phase 4",
        features=[
            "Expected LOS prediction",
            "Readmission risk scoring",
            "Bed demand forecasting",
            "Treatment cost estimation",
            "Patient outcome probability",
            "Seasonal admission forecasting",
        ],
    )

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f'<hr style="border:none; border-top:1px solid {C_BORDER}; margin:2rem 0 0.5rem 0;">', unsafe_allow_html=True)
st.markdown(
    f'<p style="font-size:0.72rem; color:{C_SUBTEXT}; text-align:center;">'
    f'MediSight · Phase 1 + Phase 2 · Data: <code>{os.path.basename(DATA_PATH)}</code> · '
    f'No data generated, modified, or written back to source.'
    f'</p>',
    unsafe_allow_html=True,
)
