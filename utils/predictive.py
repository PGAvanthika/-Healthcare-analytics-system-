# =============================================================================
# utils/predictive.py — MediSight  |  Predictive Analytics (Phase 3)
# =============================================================================
# Feature: Expected LOS Prediction
#
# Method: Historical median-based group estimation.
#   - No ML model is trained.
#   - No synthetic data is generated.
#   - All calculations run in-memory on the existing processed DataFrame.
#
# Rationale for the median:
#   LOS data is right-skewed (755 same-day records with LOS=0; max=32 days).
#   The median is more robust to extreme outliers than the mean and gives a
#   better "typical stay" estimate for clinical planning purposes.
#
# Grouping hierarchy (most → least granular):
#   Level 3: Department + Patient type + Age Bucket
#   Level 2: Department + Patient type
#   Level 1: Department only
#   Level 0: Overall (fallback)
#
# Minimum records threshold: groups with fewer than MIN_GROUP_RECORDS
# records are flagged but not suppressed — the estimate is shown with a
# low-confidence warning.
# =============================================================================

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.graph_objects as go

from config import (
    COL_LOS,
    COL_DEPT_NAME,
    COL_PATIENT_TYPE,
    COL_AGE_BUCKET,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MIN_GROUP_RECORDS = 5     # groups below this are flagged as low-confidence
AGE_ORDER = ["Below 6Y", "6-20Y", "21-40Y", "41-60y", "60+Y"]

# Chart theme tokens — mirror app.py design constants
_C_BG      = "#FFFFFF"
_C_GRID    = "#EEF2F7"
_C_AXIS    = "#64748B"
_C_TEXT    = "#17324D"
_C_TITLE   = "#123B5D"
_C_TEAL    = "#0F766E"
_C_ACCENT  = "#2A9D8F"
_C_PRIMARY = "#123B5D"
_C_AMBER   = "#D97706"
_C_LOW_CI  = "#94A3B8"   # muted colour for low-confidence bars

_BASE_LAYOUT = dict(
    paper_bgcolor=_C_BG,
    plot_bgcolor=_C_BG,
    font=dict(family="'Segoe UI', sans-serif", size=12, color=_C_TEXT),
    title_font=dict(size=14, color=_C_TITLE, family="'Segoe UI', sans-serif"),
    margin=dict(l=40, r=20, t=55, b=45),
    hoverlabel=dict(
        bgcolor="#FFFFFF",
        font_size=12,
        font_family="'Segoe UI', sans-serif",
        bordercolor="#D9E2EC",
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        font=dict(size=11, color=_C_TEXT),
    ),
)

_AXIS_STYLE  = dict(linecolor=_C_AXIS, tickfont=dict(color=_C_TEXT), title_font=dict(color=_C_TEXT))
_GRID_AXIS   = dict(**_AXIS_STYLE, showgrid=True,  gridcolor=_C_GRID)
_NO_GRID     = dict(**_AXIS_STYLE, showgrid=False)


def _empty_fig(title: str, msg: str = "No data for current filter.") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=13, color=_C_AXIS),
    )
    fig.update_layout(
        **_BASE_LAYOUT, title_text=title,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Core calculation functions
# ─────────────────────────────────────────────────────────────────────────────

def overall_los_stats(df: pd.DataFrame) -> dict:
    """
    Overall LOS summary for the KPI row.

    Returns
    -------
    dict with keys: median, mean, std, min, max, valid_count, dept_count
    """
    los = df[COL_LOS].dropna()
    if len(los) == 0:
        return {}

    dept_count = (
        int(df[COL_DEPT_NAME].nunique())
        if COL_DEPT_NAME in df.columns else 0
    )

    return {
        "median":      float(los.median()),
        "mean":        round(float(los.mean()), 2),
        "std":         round(float(los.std()), 2),
        "min":         int(los.min()),
        "max":         int(los.max()),
        "valid_count": int(len(los)),
        "dept_count":  dept_count,
    }


def los_by_department(df: pd.DataFrame) -> pd.DataFrame:
    """
    Median, mean, min, max LOS grouped by Department.

    Formula (DAX equivalent):
        Median_LOS(Dept=D) = MEDIAN(LOS WHERE Department_Name = D AND LOS IS NOT NULL)
        Mean_LOS(Dept=D)   = AVERAGE(LOS WHERE Department_Name = D AND LOS IS NOT NULL)

    Returns DataFrame sorted by Median_LOS descending.
    """
    if COL_DEPT_NAME not in df.columns or len(df) == 0:
        return pd.DataFrame()

    grp = (
        df.dropna(subset=[COL_LOS])
        .groupby(COL_DEPT_NAME, observed=True)[COL_LOS]
        .agg(
            Records     = "count",
            Median_LOS  = "median",
            Mean_LOS    = "mean",
            Min_LOS     = "min",
            Max_LOS     = "max",
            Std_LOS     = "std",
        )
        .reset_index()
        .rename(columns={COL_DEPT_NAME: "Department"})
        .sort_values("Median_LOS", ascending=False)
    )
    for col in ["Median_LOS", "Mean_LOS", "Std_LOS"]:
        grp[col] = grp[col].round(2)
    grp["Low_Confidence"] = grp["Records"] < MIN_GROUP_RECORDS
    return grp


def los_by_dept_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    Median LOS grouped by Department × Patient type.
    Primary grouping for the results table when no Age Bucket is selected.
    """
    if COL_DEPT_NAME not in df.columns or COL_PATIENT_TYPE not in df.columns:
        return pd.DataFrame()

    grp = (
        df.dropna(subset=[COL_LOS])
        .groupby([COL_DEPT_NAME, COL_PATIENT_TYPE], observed=True)[COL_LOS]
        .agg(
            Records    = "count",
            Median_LOS = "median",
            Mean_LOS   = "mean",
            Min_LOS    = "min",
            Max_LOS    = "max",
        )
        .reset_index()
        .rename(columns={
            COL_DEPT_NAME:    "Department",
            COL_PATIENT_TYPE: "Patient Type",
        })
        .sort_values(["Department", "Patient Type"])
    )
    for col in ["Median_LOS", "Mean_LOS"]:
        grp[col] = grp[col].round(2)
    grp["Low_Confidence"] = grp["Records"] < MIN_GROUP_RECORDS
    return grp


def los_by_dept_type_age(df: pd.DataFrame) -> pd.DataFrame:
    """
    Median LOS grouped by Department × Patient type × Age Bucket.
    Used when Age Bucket filter is active.
    """
    required = [COL_DEPT_NAME, COL_PATIENT_TYPE, COL_AGE_BUCKET]
    if not all(c in df.columns for c in required):
        return pd.DataFrame()

    grp = (
        df.dropna(subset=[COL_LOS])
        .groupby([COL_DEPT_NAME, COL_PATIENT_TYPE, COL_AGE_BUCKET], observed=True)[COL_LOS]
        .agg(
            Records    = "count",
            Median_LOS = "median",
            Mean_LOS   = "mean",
            Min_LOS    = "min",
            Max_LOS    = "max",
        )
        .reset_index()
        .rename(columns={
            COL_DEPT_NAME:    "Department",
            COL_PATIENT_TYPE: "Patient Type",
            COL_AGE_BUCKET:   "Age Bucket",
        })
    )
    # Sort Age Bucket in logical order
    present_ages = [a for a in AGE_ORDER if a in grp["Age Bucket"].values]
    grp["Age Bucket"] = pd.Categorical(grp["Age Bucket"], categories=present_ages, ordered=True)
    grp = grp.sort_values(["Department", "Patient Type", "Age Bucket"])

    for col in ["Median_LOS", "Mean_LOS"]:
        grp[col] = grp[col].round(2)
    grp["Low_Confidence"] = grp["Records"] < MIN_GROUP_RECORDS
    return grp


def estimate_los(
    df: pd.DataFrame,
    department: str | None,
    patient_type: str | None,
    age_bucket: str | None,
) -> dict:
    """
    Return the expected LOS estimate for a specific patient group.
    Falls back to a coarser grouping if the exact match has no records.

    Hierarchy (most → least specific):
        1. Department + Patient type + Age Bucket  (if all provided)
        2. Department + Patient type               (if dept + type provided)
        3. Department only                         (if only dept provided)
        4. Overall median                          (final fallback)

    Returns
    -------
    dict:
        expected_los      float   median LOS for the matched group
        mean_los          float
        records           int     number of records in the matched group
        level             str     which grouping level was used
        low_confidence    bool    True if records < MIN_GROUP_RECORDS
        no_data           bool    True if no valid records found at any level
    """
    valid = df.dropna(subset=[COL_LOS])

    # Build progressive filters
    def _filter(d, dept, ptype, age):
        mask = pd.Series([True] * len(d), index=d.index)
        if dept  and COL_DEPT_NAME    in d.columns: mask &= d[COL_DEPT_NAME]    == dept
        if ptype and COL_PATIENT_TYPE in d.columns: mask &= d[COL_PATIENT_TYPE] == ptype
        if age   and COL_AGE_BUCKET   in d.columns: mask &= d[COL_AGE_BUCKET]   == age
        return d[mask]

    # Try levels from most to least specific
    attempts = []
    if department and patient_type and age_bucket:
        attempts.append((department, patient_type, age_bucket,
                         "Department + Patient Type + Age Bucket"))
    if department and patient_type:
        attempts.append((department, patient_type, None,
                         "Department + Patient Type"))
    if department:
        attempts.append((department, None, None, "Department"))
    attempts.append((None, None, None, "Overall (all records)"))

    for dept, ptype, age, level in attempts:
        subset = _filter(valid, dept, ptype, age)
        if len(subset) > 0:
            los_vals = subset[COL_LOS]
            return {
                "expected_los":   round(float(los_vals.median()), 2),
                "mean_los":       round(float(los_vals.mean()),   2),
                "records":        int(len(los_vals)),
                "level":          level,
                "low_confidence": int(len(los_vals)) < MIN_GROUP_RECORDS,
                "no_data":        False,
            }

    return {
        "expected_los":   0.0,
        "mean_los":       0.0,
        "records":        0,
        "level":          "—",
        "low_confidence": True,
        "no_data":        True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chart functions
# ─────────────────────────────────────────────────────────────────────────────

def plot_median_los_by_department(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart: median LOS per department, sorted descending.
    Low-confidence bars (< MIN_GROUP_RECORDS) are rendered in a muted colour.
    """
    dept_stats = los_by_department(df)
    if dept_stats.empty:
        return _empty_fig("Median LOS by Department")

    dept_stats = dept_stats.sort_values("Median_LOS", ascending=True)

    colours = [
        _C_LOW_CI if lc else _C_PRIMARY
        for lc in dept_stats["Low_Confidence"]
    ]
    text_labels = [
        f"{v:.1f}d {'⚠' if lc else ''}"
        for v, lc in zip(dept_stats["Median_LOS"], dept_stats["Low_Confidence"])
    ]

    fig = go.Figure(go.Bar(
        x=dept_stats["Median_LOS"],
        y=dept_stats["Department"],
        orientation="h",
        marker_color=colours,
        text=text_labels,
        textposition="outside",
        customdata=dept_stats[["Mean_LOS", "Records", "Min_LOS", "Max_LOS"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Median LOS: %{x:.1f} days<br>"
            "Mean LOS: %{customdata[0]:.2f} days<br>"
            "Records: %{customdata[1]:,}<br>"
            "Range: %{customdata[2]} – %{customdata[3]} days"
            "<extra></extra>"
        ),
    ))

    height = max(320, len(dept_stats) * 46 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Expected LOS by Department (Historical Median)",
        xaxis=dict(**_GRID_AXIS, title="Median LOS (days)",
                   range=[0, dept_stats["Median_LOS"].max() * 1.25]),
        yaxis=dict(**_NO_GRID, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=70, t=55, b=40),
    )
    return fig


def plot_median_los_by_dept_type(df: pd.DataFrame) -> go.Figure:
    """
    Grouped horizontal bar: median LOS per department, broken down by patient type.
    """
    if COL_DEPT_NAME not in df.columns or COL_PATIENT_TYPE not in df.columns or len(df) == 0:
        return _empty_fig("Median LOS by Department & Patient Type")

    valid = df.dropna(subset=[COL_LOS])
    grp = (
        valid.groupby([COL_DEPT_NAME, COL_PATIENT_TYPE], observed=True)[COL_LOS]
        .agg(Median="median", Count="count")
        .reset_index()
    )
    if grp.empty:
        return _empty_fig("Median LOS by Department & Patient Type")

    patient_types = sorted(grp[COL_PATIENT_TYPE].unique())
    type_colours  = {
        pt: col for pt, col in zip(
            sorted(patient_types),
            [_C_PRIMARY, _C_ACCENT, _C_TEAL, _C_AMBER],
        )
    }

    # Order departments by overall median LOS descending
    dept_order = (
        valid.groupby(COL_DEPT_NAME)[COL_LOS]
        .median()
        .sort_values(ascending=True)
        .index.tolist()
    )

    fig = go.Figure()
    for pt in patient_types:
        sub = grp[grp[COL_PATIENT_TYPE] == pt]
        fig.add_trace(go.Bar(
            name=pt,
            x=sub["Median"],
            y=sub[COL_DEPT_NAME],
            orientation="h",
            marker_color=type_colours.get(pt, _C_TEAL),
            hovertemplate=(
                f"<b>%{{y}}</b> · {pt}<br>"
                "Median LOS: %{x:.1f} days<br>"
                "Records: %{customdata:,}<extra></extra>"
            ),
            customdata=sub["Count"].values,
        ))

    height = max(320, len(dept_order) * 50 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k not in ("margin", "legend")}
    fig.update_layout(
        **layout,
        title_text="Median LOS by Department & Patient Type",
        barmode="group",
        xaxis=dict(**_GRID_AXIS, title="Median LOS (days)"),
        yaxis=dict(**_NO_GRID, title="", automargin=True,
                   categoryorder="array", categoryarray=dept_order),
        height=height,
        margin=dict(l=10, r=20, t=55, b=40),
        legend=dict(orientation="h", y=-0.12, x=0, font=dict(size=11, color=_C_TEXT)),
    )
    return fig


def plot_los_distribution_by_type(df: pd.DataFrame) -> go.Figure:
    """
    Overlapping histogram of LOS distribution for Inpatients vs Outpatients.
    Outpatients (LOS=0) are separated to show the bimodal nature of the data.
    """
    if COL_PATIENT_TYPE not in df.columns or len(df) == 0:
        return _empty_fig("LOS Distribution by Patient Type")

    valid = df.dropna(subset=[COL_LOS])
    patient_types = sorted(valid[COL_PATIENT_TYPE].unique())
    type_colours  = {
        "Inpatient":  _C_PRIMARY,
        "outpatient": _C_ACCENT,
    }

    fig = go.Figure()
    for pt in patient_types:
        sub = valid[valid[COL_PATIENT_TYPE] == pt][COL_LOS]
        if len(sub) == 0:
            continue
        fig.add_trace(go.Histogram(
            x=sub,
            name=pt,
            nbinsx=20,
            marker_color=type_colours.get(pt, _C_TEAL),
            opacity=0.75,
            hovertemplate=f"<b>{pt}</b><br>LOS: %{{x}} days<br>Count: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="LOS Distribution by Patient Type",
        barmode="overlay",
        xaxis=dict(**_NO_GRID, title="Length of Stay (days)"),
        yaxis=dict(**_GRID_AXIS, title="Number of Patients"),
    )
    return fig
