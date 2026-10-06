# =============================================================================
# utils/diagnostic.py — MediSight Phase 2  |  Diagnostic Analytics
# =============================================================================
# Four analysis modules, each returning Plotly figures and summary DataFrames
# computed entirely in-memory from the filtered patient DataFrame.
#
# RULES
# -----
# - No file I/O, no new datasets, no ML models.
# - Every threshold is calculated from the data using quantiles/percentiles,
#   not arbitrary magic numbers.
# - Categorical "correlation" is framed as association / pattern, never
#   stated as causation.
# - If a required column (e.g. Diagnosis) is absent from the source data,
#   the analysis is clearly labelled as unavailable and a safe fallback is
#   used with an honest label.
# - All functions accept the already-filtered patient DataFrame so they
#   respond automatically to the global sidebar filters.
# =============================================================================

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    COL_STATUS,
    COL_PATIENT_TYPE,
    COL_AGE_BUCKET,
    COL_DEPT_NAME,
    COL_LOS,
    COL_ER_TIME,
    COL_TREATMENT_COST,
    STATUS_READMIT,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared chart theme  (mirrors app.py design tokens)
# ─────────────────────────────────────────────────────────────────────────────

_C_BG      = "#FFFFFF"
_C_GRID    = "#EEF2F7"
_C_AXIS    = "#64748B"
_C_TEXT    = "#17324D"
_C_TITLE   = "#123B5D"
_C_TEAL    = "#0F766E"
_C_ACCENT  = "#2A9D8F"
_C_PRIMARY = "#123B5D"
_C_AMBER   = "#D97706"
_C_RED     = "#B91C1C"
_C_GREEN   = "#0F766E"

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

_AXIS_STYLE = dict(
    linecolor=_C_AXIS,
    tickfont=dict(color=_C_TEXT),
    title_font=dict(color=_C_TEXT),
)
_GRID_AXIS = dict(**_AXIS_STYLE, showgrid=True, gridcolor=_C_GRID)
_NO_GRID_AXIS = dict(**_AXIS_STYLE, showgrid=False)


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
# Threshold helpers — all derived from the data, never hardcoded
# ─────────────────────────────────────────────────────────────────────────────

def compute_er_thresholds(df: pd.DataFrame) -> tuple[float, float]:
    """
    Return (low_cut, high_cut) for ER_Wait_Category using Q33/Q66 of valid
    ER_Time values in the supplied DataFrame.

    ER_Wait_Category:
        Short    ≤ Q33
        Moderate Q33 < x ≤ Q66
        Long     > Q66
    """
    er = df[COL_ER_TIME].dropna()
    if len(er) < 3:
        return (35.0, 60.0)          # fallback only if virtually no data
    return float(er.quantile(0.33)), float(er.quantile(0.66))


def compute_los_thresholds(df: pd.DataFrame) -> tuple[float, float]:
    """
    Return (low_cut, high_cut) for LOS_Category using Q33/Q66.

    LOS_Category:
        Short    ≤ Q33
        Normal   Q33 < x ≤ Q66
        Prolonged > Q66
    """
    los = df[COL_LOS].dropna()
    if len(los) < 3:
        return (1.0, 2.0)
    return float(los.quantile(0.33)), float(los.quantile(0.66))


def compute_cost_thresholds(df: pd.DataFrame) -> tuple[float, float]:
    """
    Return (low_cut, high_cut) for Cost_Category using Q33/Q66.

    Cost_Category:
        Low    ≤ Q33
        Medium Q33 < x ≤ Q66
        High   > Q66
    """
    cost = df[COL_TREATMENT_COST].dropna()
    if len(cost) < 3:
        return (21.92, 167.73)
    return float(cost.quantile(0.33)), float(cost.quantile(0.66))


def add_derived_diagnostic_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ER_Wait_Category, LOS_Category, and Cost_Category to df.
    Thresholds are computed from the passed DataFrame so they adapt to filters.
    The original df is not mutated.
    """
    df = df.copy()

    # ── ER_Wait_Category ──────────────────────────────────────
    er_low, er_high = compute_er_thresholds(df)
    def _er_cat(v):
        if pd.isna(v):
            return np.nan
        if v <= er_low:
            return "Short"
        if v <= er_high:
            return "Moderate"
        return "Long"
    df["ER_Wait_Category"] = df[COL_ER_TIME].apply(_er_cat)

    # ── LOS_Category ──────────────────────────────────────────
    los_low, los_high = compute_los_thresholds(df)
    def _los_cat(v):
        if pd.isna(v):
            return np.nan
        if v <= los_low:
            return "Short Stay"
        if v <= los_high:
            return "Normal Stay"
        return "Prolonged Stay"
    df["LOS_Category"] = df[COL_LOS].apply(_los_cat)

    # ── Cost_Category ─────────────────────────────────────────
    cost_low, cost_high = compute_cost_thresholds(df)
    def _cost_cat(v):
        if pd.isna(v):
            return np.nan
        if v <= cost_low:
            return "Low"
        if v <= cost_high:
            return "Medium"
        return "High"
    df["Cost_Category"] = df[COL_TREATMENT_COST].apply(_cost_cat)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# MODULE A — Readmission Analysis
# ─────────────────────────────────────────────────────────────────────────────

def readmission_summary(df: pd.DataFrame) -> dict:
    """
    Return scalar summary metrics for the readmission analysis section.

    All values are DAX-equivalent Pandas measures, computed dynamically.
    """
    total      = len(df)
    readmitted = int((df[COL_STATUS] == STATUS_READMIT).sum())
    rate       = round(readmitted / total * 100, 1) if total else 0.0

    return {
        "total_patients":      total,
        "readmitted":          readmitted,
        "readmission_rate_pct": rate,
    }


def _readmission_rate_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Compute readmission count and rate grouped by col.
    Returns DataFrame with columns: [col, Total, Readmit, Rate_%].
    """
    if col not in df.columns or len(df) == 0:
        return pd.DataFrame()
    grp = (
        df.groupby(col, observed=True)
        .agg(
            Total   = (COL_STATUS, "count"),
            Readmit = (COL_STATUS, lambda x: (x == STATUS_READMIT).sum()),
        )
        .reset_index()
    )
    grp["Rate_%"] = (grp["Readmit"] / grp["Total"] * 100).round(1)
    return grp.sort_values("Rate_%", ascending=False)


def plot_readmission_by_department(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar — readmission rate (%) by department."""
    grp = _readmission_rate_by(df, COL_DEPT_NAME)
    if grp.empty:
        return _empty_fig("Readmission Rate by Department")

    grp = grp.sort_values("Rate_%", ascending=True)          # largest at top
    colours = [_C_RED if r >= 20 else _C_AMBER if r >= 10 else _C_TEAL
               for r in grp["Rate_%"]]

    fig = go.Figure(go.Bar(
        x=grp["Rate_%"], y=grp[COL_DEPT_NAME],
        orientation="h",
        marker_color=colours,
        text=grp["Rate_%"].apply(lambda v: f"{v}%"),
        textposition="outside",
        customdata=grp[["Total","Readmit"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Readmission Rate: %{x:.1f}%<br>"
            "Readmitted: %{customdata[1]:,}<br>"
            "Total Patients: %{customdata[0]:,}<extra></extra>"
        ),
    ))
    height = max(300, len(grp) * 44 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Readmission Rate by Department",
        xaxis=dict(**_GRID_AXIS, title="Readmission Rate (%)", range=[0, grp["Rate_%"].max() * 1.18]),
        yaxis=dict(**_NO_GRID_AXIS, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=60, t=55, b=40),
    )
    return fig


def plot_readmission_by_patient_type(df: pd.DataFrame) -> go.Figure:
    """Grouped bar — readmission vs non-readmission counts by patient type."""
    grp = _readmission_rate_by(df, COL_PATIENT_TYPE)
    if grp.empty:
        return _empty_fig("Readmission by Patient Type")

    grp["Non-Readmit"] = grp["Total"] - grp["Readmit"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Readmitted",
        x=grp[COL_PATIENT_TYPE], y=grp["Readmit"],
        marker_color=_C_RED,
        text=grp["Rate_%"].apply(lambda v: f"{v}%"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Readmitted: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Not Readmitted",
        x=grp[COL_PATIENT_TYPE], y=grp["Non-Readmit"],
        marker_color=_C_TEAL,
        hovertemplate="<b>%{x}</b><br>Not Readmitted: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Readmission by Patient Type",
        barmode="group",
        xaxis=dict(**_NO_GRID_AXIS, title="Patient Type"),
        yaxis=dict(**_GRID_AXIS, title="Patient Count"),
    )
    return fig


def plot_readmission_by_age_bucket(df: pd.DataFrame) -> go.Figure:
    """Bar chart — readmission rate by age group in logical age order."""
    AGE_ORDER = ["Below 6Y", "6-20Y", "21-40Y", "41-60y", "60+Y"]
    grp = _readmission_rate_by(df, COL_AGE_BUCKET)
    if grp.empty:
        return _empty_fig("Readmission Rate by Age Group")

    present = [b for b in AGE_ORDER if b in grp[COL_AGE_BUCKET].values]
    grp[COL_AGE_BUCKET] = pd.Categorical(grp[COL_AGE_BUCKET], categories=present, ordered=True)
    grp = grp.sort_values(COL_AGE_BUCKET)

    colours = [_C_RED if r >= 20 else _C_AMBER if r >= 10 else _C_TEAL
               for r in grp["Rate_%"]]

    fig = go.Figure(go.Bar(
        x=grp[COL_AGE_BUCKET].astype(str), y=grp["Rate_%"],
        marker_color=colours,
        text=grp["Rate_%"].apply(lambda v: f"{v}%"),
        textposition="outside",
        customdata=grp[["Total","Readmit"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Readmission Rate: %{y:.1f}%<br>"
            "Readmitted: %{customdata[1]:,} / %{customdata[0]:,}<extra></extra>"
        ),
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Readmission Rate by Age Group",
        xaxis=dict(**_NO_GRID_AXIS, title="Age Group"),
        yaxis=dict(**_GRID_AXIS, title="Readmission Rate (%)"),
    )
    return fig


def plot_readmission_by_category(df: pd.DataFrame, category_col: str,
                                  title: str) -> go.Figure:
    """
    Generic bar — readmission rate by a derived category column
    (ER_Wait_Category, LOS_Category, Cost_Category).
    """
    if category_col not in df.columns:
        return _empty_fig(title, "Category column not available.")

    # Define desired display order per category type
    order_map = {
        "ER_Wait_Category": ["Short", "Moderate", "Long"],
        "LOS_Category":     ["Short Stay", "Normal Stay", "Prolonged Stay"],
        "Cost_Category":    ["Low", "Medium", "High"],
    }
    grp = _readmission_rate_by(df.dropna(subset=[category_col]), category_col)
    if grp.empty:
        return _empty_fig(title)

    order = order_map.get(category_col, sorted(grp[category_col].unique()))
    present = [o for o in order if o in grp[category_col].values]
    grp[category_col] = pd.Categorical(grp[category_col], categories=present, ordered=True)
    grp = grp.sort_values(category_col)

    colours = [_C_RED if r >= 20 else _C_AMBER if r >= 10 else _C_TEAL
               for r in grp["Rate_%"]]

    fig = go.Figure(go.Bar(
        x=grp[category_col].astype(str), y=grp["Rate_%"],
        marker_color=colours,
        text=grp["Rate_%"].apply(lambda v: f"{v}%"),
        textposition="outside",
        customdata=grp[["Total","Readmit"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Readmission Rate: %{y:.1f}%<br>"
            "Readmitted: %{customdata[1]:,} / %{customdata[0]:,}<extra></extra>"
        ),
    ))
    fig.update_layout(
        **_BASE_LAYOUT, title_text=title,
        xaxis=dict(**_NO_GRID_AXIS, title=category_col.replace("_", " ")),
        yaxis=dict(**_GRID_AXIS, title="Readmission Rate (%)"),
    )
    return fig


def readmission_breakdown_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a combined breakdown table for all readmission factors.
    Used in the summary dataframe display.
    """
    rows = []
    for col, label in [
        (COL_DEPT_NAME,    "Department"),
        (COL_PATIENT_TYPE, "Patient Type"),
        (COL_AGE_BUCKET,   "Age Group"),
        ("ER_Wait_Category","ER Wait Category"),
        ("LOS_Category",   "LOS Category"),
        ("Cost_Category",  "Cost Category"),
    ]:
        if col not in df.columns:
            continue
        grp = _readmission_rate_by(df.dropna(subset=[col]), col)
        if grp.empty:
            continue
        grp = grp.rename(columns={col: "Value"})
        grp.insert(0, "Factor", label)
        rows.append(grp[["Factor","Value","Total","Readmit","Rate_%"]])

    if not rows:
        return pd.DataFrame(columns=["Factor","Value","Total","Readmit","Rate_%"])
    return pd.concat(rows, ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# MODULE B — ER Wait-Time Analysis
# ─────────────────────────────────────────────────────────────────────────────

def er_summary_stats(df: pd.DataFrame) -> dict:
    """Return descriptive stats for ER_Time."""
    er = df[COL_ER_TIME].dropna()
    if len(er) == 0:
        return {}
    return {
        "count":   int(len(er)),
        "missing": int(df[COL_ER_TIME].isna().sum()),
        "mean":    round(float(er.mean()), 1),
        "median":  round(float(er.median()), 1),
        "std":     round(float(er.std()), 1),
        "min":     round(float(er.min()), 1),
        "max":     round(float(er.max()), 1),
        "p25":     round(float(er.quantile(0.25)), 1),
        "p75":     round(float(er.quantile(0.75)), 1),
        "p90":     round(float(er.quantile(0.90)), 1),
    }


def plot_er_distribution(df: pd.DataFrame) -> go.Figure:
    """Histogram of ER_Time with a median reference line."""
    er = df[COL_ER_TIME].dropna()
    if len(er) == 0:
        return _empty_fig("ER Wait-Time Distribution")

    median_val = er.median()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=er, nbinsx=30,
        marker_color=_C_TEAL,
        marker_line=dict(color=_C_BG, width=0.5),
        opacity=0.85,
        name="ER Time",
        hovertemplate="ER Time: %{x:.0f} min<br>Count: %{y}<extra></extra>",
    ))
    fig.add_vline(
        x=median_val, line_dash="dash", line_color=_C_RED, line_width=1.5,
        annotation_text=f"Median: {median_val:.0f} min",
        annotation_position="top right",
        annotation_font=dict(color=_C_RED, size=11),
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="ER Wait-Time Distribution",
        xaxis=dict(**_NO_GRID_AXIS, title="ER Time (minutes)"),
        yaxis=dict(**_GRID_AXIS, title="Number of Patients"),
    )
    return fig


def plot_er_by_department(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar — average ER time per department (patients with ER_Time only)."""
    er_df = df.dropna(subset=[COL_ER_TIME, COL_DEPT_NAME])
    if len(er_df) == 0:
        return _empty_fig("Avg ER Time by Department")

    grp = (
        er_df.groupby(COL_DEPT_NAME)[COL_ER_TIME]
        .agg(Mean="mean", Median="median", Count="count")
        .reset_index()
        .sort_values("Mean", ascending=True)
    )
    grp["Mean"]   = grp["Mean"].round(1)
    grp["Median"] = grp["Median"].round(1)

    fig = go.Figure(go.Bar(
        x=grp["Mean"], y=grp[COL_DEPT_NAME],
        orientation="h",
        marker_color=_C_TEAL,
        text=grp["Mean"].apply(lambda v: f"{v} min"),
        textposition="outside",
        customdata=grp[["Median","Count"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Avg ER Time: %{x:.1f} min<br>"
            "Median: %{customdata[0]:.1f} min<br>"
            "Patients with ER data: %{customdata[1]:,}<extra></extra>"
        ),
    ))
    height = max(300, len(grp) * 44 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Avg ER Wait Time by Department",
        xaxis=dict(**_GRID_AXIS, title="Average ER Time (minutes)",
                   range=[0, grp["Mean"].max() * 1.18]),
        yaxis=dict(**_NO_GRID_AXIS, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=60, t=55, b=40),
    )
    return fig


def plot_er_wait_category_dist(df: pd.DataFrame) -> go.Figure:
    """Donut of ER_Wait_Category distribution."""
    if "ER_Wait_Category" not in df.columns:
        return _empty_fig("ER Wait Category Distribution")

    counts = df["ER_Wait_Category"].dropna().value_counts()
    if len(counts) == 0:
        return _empty_fig("ER Wait Category Distribution")

    order   = ["Short", "Moderate", "Long"]
    colours = [_C_TEAL, _C_AMBER, _C_RED]
    labels  = [c for c in order if c in counts.index]
    values  = [int(counts.get(c, 0)) for c in labels]
    cols    = [colours[order.index(c)] for c in labels]

    er_low, er_high = compute_er_thresholds(df)
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.42,
        marker=dict(colors=cols, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Patients: %{value:,}<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text=f"ER Wait Category (Short ≤{er_low:.0f} min · Long >{er_high:.0f} min)",
        showlegend=True,
    )
    return fig


def plot_er_vs_los_scatter(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot: ER_Time (x) vs LOS (y), coloured by patient type.
    Only rows with valid ER_Time are shown (1787 of 2506 full-data records).
    """
    scatter_df = df.dropna(subset=[COL_ER_TIME]).copy()
    if len(scatter_df) == 0:
        return _empty_fig("ER Time vs Length of Stay")

    type_colours = {"Inpatient": _C_PRIMARY, "outpatient": _C_ACCENT}
    patient_types = scatter_df[COL_PATIENT_TYPE].dropna().unique() if COL_PATIENT_TYPE in scatter_df.columns else []

    fig = go.Figure()
    if len(patient_types) > 0:
        for pt in sorted(patient_types):
            subset = scatter_df[scatter_df[COL_PATIENT_TYPE] == pt]
            fig.add_trace(go.Scatter(
                x=subset[COL_ER_TIME], y=subset[COL_LOS],
                mode="markers",
                name=str(pt),
                marker=dict(
                    color=type_colours.get(pt, _C_TEAL),
                    size=5, opacity=0.55,
                ),
                hovertemplate=(
                    f"<b>{pt}</b><br>"
                    "ER Time: %{x:.0f} min<br>"
                    "LOS: %{y} days<extra></extra>"
                ),
            ))
    else:
        fig.add_trace(go.Scatter(
            x=scatter_df[COL_ER_TIME], y=scatter_df[COL_LOS],
            mode="markers",
            marker=dict(color=_C_TEAL, size=5, opacity=0.5),
            hovertemplate="ER Time: %{x:.0f} min<br>LOS: %{y} days<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="ER Wait Time vs Length of Stay",
        xaxis=dict(**_NO_GRID_AXIS, title="ER Time (minutes)"),
        yaxis=dict(**_GRID_AXIS, title="Length of Stay (days)"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MODULE C — LOS vs Department Analysis
# ─────────────────────────────────────────────────────────────────────────────

def los_by_department_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return per-department LOS statistics.
    Department is categorical so a Pearson correlation with raw department
    names is not appropriate — per-group stats are used instead.
    """
    if COL_DEPT_NAME not in df.columns or len(df) == 0:
        return pd.DataFrame()

    grp = (
        df.groupby(COL_DEPT_NAME)[COL_LOS]
        .agg(
            Patients = "count",
            Mean_LOS = "mean",
            Median_LOS = "median",
            Min_LOS  = "min",
            Max_LOS  = "max",
            Std_LOS  = "std",
        )
        .reset_index()
        .sort_values("Mean_LOS", ascending=False)
    )
    grp["Mean_LOS"]   = grp["Mean_LOS"].round(2)
    grp["Median_LOS"] = grp["Median_LOS"].round(2)
    grp["Std_LOS"]    = grp["Std_LOS"].round(2)
    grp.rename(columns={COL_DEPT_NAME: "Department"}, inplace=True)
    return grp


def plot_avg_los_by_department(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar — average LOS per department."""
    stats = los_by_department_stats(df)
    if stats.empty:
        return _empty_fig("Avg LOS by Department")

    stats_sorted = stats.sort_values("Mean_LOS", ascending=True)

    fig = go.Figure(go.Bar(
        x=stats_sorted["Mean_LOS"], y=stats_sorted["Department"],
        orientation="h",
        marker_color=_C_PRIMARY,
        text=stats_sorted["Mean_LOS"].apply(lambda v: f"{v:.1f}d"),
        textposition="outside",
        customdata=stats_sorted[["Median_LOS","Patients","Std_LOS"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Mean LOS: %{x:.2f} days<br>"
            "Median LOS: %{customdata[0]:.2f} days<br>"
            "Patients: %{customdata[1]:,}<br>"
            "Std Dev: %{customdata[2]:.2f}<extra></extra>"
        ),
    ))
    height = max(300, len(stats_sorted) * 44 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Average Length of Stay by Department",
        xaxis=dict(**_GRID_AXIS, title="Average LOS (days)",
                   range=[0, stats_sorted["Mean_LOS"].max() * 1.2]),
        yaxis=dict(**_NO_GRID_AXIS, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=60, t=55, b=40),
    )
    return fig


def plot_los_box_by_department(df: pd.DataFrame) -> go.Figure:
    """
    Box plot of LOS distribution by department.
    Shows spread, median, IQR, and outliers per department.
    """
    if COL_DEPT_NAME not in df.columns or len(df) == 0:
        return _empty_fig("LOS Distribution by Department")

    # Order departments by median LOS descending
    order = (
        df.groupby(COL_DEPT_NAME)[COL_LOS]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    # Assign a consistent colour per department for readability
    palette = [_C_PRIMARY, _C_TEAL, _C_ACCENT, _C_AMBER,
               "#7C3AED", "#0891B2", "#0F766E", "#1D4ED8", "#B45309", "#6D28D9"]
    colour_map = {dept: palette[i % len(palette)] for i, dept in enumerate(order)}

    fig = go.Figure()
    for dept in order:
        subset = df[df[COL_DEPT_NAME] == dept][COL_LOS].dropna()
        if len(subset) == 0:
            continue
        fig.add_trace(go.Box(
            y=subset,
            name=dept,
            marker_color=colour_map[dept],
            line_color=colour_map[dept],
            boxmean="sd",
            hovertemplate=f"<b>{dept}</b><br>LOS: %{{y}} days<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="LOS Distribution by Department",
        xaxis=dict(**_NO_GRID_AXIS, title="Department", tickangle=-30),
        yaxis=dict(**_GRID_AXIS, title="Length of Stay (days)"),
        showlegend=False,
        height=420,
    )
    return fig


def plot_los_vs_cost(df: pd.DataFrame) -> go.Figure:
    """
    Scatter: LOS (x) vs treatment cost (y), coloured by patient type.
    A Pearson correlation between two numeric variables is appropriate here.
    """
    scatter_df = df.dropna(subset=[COL_LOS, COL_TREATMENT_COST]).copy()
    if len(scatter_df) < 2:
        return _empty_fig("LOS vs Treatment Cost")

    # Pearson r between two numeric columns — appropriate
    r = scatter_df[COL_LOS].corr(scatter_df[COL_TREATMENT_COST])

    type_colours = {"Inpatient": _C_PRIMARY, "outpatient": _C_ACCENT}
    patient_types = (
        scatter_df[COL_PATIENT_TYPE].dropna().unique()
        if COL_PATIENT_TYPE in scatter_df.columns else []
    )

    fig = go.Figure()
    if len(patient_types) > 0:
        for pt in sorted(patient_types):
            sub = scatter_df[scatter_df[COL_PATIENT_TYPE] == pt]
            fig.add_trace(go.Scatter(
                x=sub[COL_LOS], y=sub[COL_TREATMENT_COST],
                mode="markers", name=str(pt),
                marker=dict(color=type_colours.get(pt, _C_TEAL), size=5, opacity=0.5),
                hovertemplate=(
                    f"<b>{pt}</b><br>"
                    "LOS: %{x} days<br>"
                    "Cost: $%{y:,.2f}<extra></extra>"
                ),
            ))
    else:
        fig.add_trace(go.Scatter(
            x=scatter_df[COL_LOS], y=scatter_df[COL_TREATMENT_COST],
            mode="markers",
            marker=dict(color=_C_TEAL, size=5, opacity=0.5),
            hovertemplate="LOS: %{x} days<br>Cost: $%{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title_text=f"LOS vs Treatment Cost  (Pearson r = {r:.2f})",
        xaxis=dict(**_NO_GRID_AXIS, title="Length of Stay (days)"),
        yaxis=dict(**_GRID_AXIS, title="Treatment Cost ($)"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MODULE D — Treatment Cost Analysis
# ─────────────────────────────────────────────────────────────────────────────
# NOTE ON DIAGNOSIS
# The source workbook (verified at Phase 1 inspection) does NOT contain a
# Diagnosis column in any sheet. No diagnosis-equivalent can be safely
# derived from Department, Age, Gender, or Status without fabricating
# clinical information. The cost analysis therefore uses Department_Name as
# the grouping variable and is labelled
# "Treatment Cost Distribution by Department" — NOT "by Diagnosis".
# ─────────────────────────────────────────────────────────────────────────────

DIAGNOSIS_AVAILABLE = False
DIAGNOSIS_NOTE = (
    "ℹ️ The source dataset does not contain a Diagnosis column in any workbook "
    "sheet. Diagnosis-level cost analysis cannot be performed on this data. "
    "The analysis below uses **Department** as the clinical grouping variable "
    "and is labelled accordingly."
)


def cost_by_department_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per-department treatment cost statistics — DAX equivalent measures."""
    if COL_DEPT_NAME not in df.columns or len(df) == 0:
        return pd.DataFrame()

    grp = (
        df.groupby(COL_DEPT_NAME)[COL_TREATMENT_COST]
        .agg(
            Patients       = "count",
            Total_Revenue  = "sum",
            Mean_Cost      = "mean",
            Median_Cost    = "median",
            Min_Cost       = "min",
            Max_Cost       = "max",
            Std_Cost       = "std",
            Q25            = lambda x: x.quantile(0.25),
            Q75            = lambda x: x.quantile(0.75),
        )
        .reset_index()
        .sort_values("Mean_Cost", ascending=False)
    )
    for col in ["Total_Revenue","Mean_Cost","Median_Cost","Min_Cost","Max_Cost","Std_Cost","Q25","Q75"]:
        grp[col] = grp[col].round(2)
    grp.rename(columns={COL_DEPT_NAME: "Department"}, inplace=True)
    return grp


def plot_cost_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of treatemencost with median reference line."""
    cost = df[COL_TREATMENT_COST].dropna()
    if len(cost) == 0:
        return _empty_fig("Treatment Cost Distribution")

    median_val = cost.median()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=cost, nbinsx=40,
        marker_color=_C_TEAL,
        marker_line=dict(color=_C_BG, width=0.4),
        opacity=0.85,
        name="Cost",
        hovertemplate="Cost: $%{x:,.0f}<br>Count: %{y}<extra></extra>",
    ))
    fig.add_vline(
        x=median_val, line_dash="dash", line_color=_C_RED, line_width=1.5,
        annotation_text=f"Median: ${median_val:,.0f}",
        annotation_position="top right",
        annotation_font=dict(color=_C_RED, size=11),
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Treatment Cost Distribution",
        xaxis=dict(**_NO_GRID_AXIS, title="Treatment Cost ($)"),
        yaxis=dict(**_GRID_AXIS, title="Number of Patients"),
    )
    return fig


def plot_cost_box_by_department(df: pd.DataFrame) -> go.Figure:
    """
    Box plot of treatment cost by department.
    Clearly labelled as department-level — not diagnosis-level.
    """
    if COL_DEPT_NAME not in df.columns or len(df) == 0:
        return _empty_fig("Treatment Cost by Department")

    order = (
        df.groupby(COL_DEPT_NAME)[COL_TREATMENT_COST]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    palette = [_C_PRIMARY, _C_TEAL, _C_ACCENT, _C_AMBER,
               "#7C3AED", "#0891B2", "#0F766E", "#1D4ED8", "#B45309", "#6D28D9"]
    colour_map = {dept: palette[i % len(palette)] for i, dept in enumerate(order)}

    fig = go.Figure()
    for dept in order:
        sub = df[df[COL_DEPT_NAME] == dept][COL_TREATMENT_COST].dropna()
        if len(sub) == 0:
            continue
        fig.add_trace(go.Box(
            y=sub, name=dept,
            marker_color=colour_map[dept],
            line_color=colour_map[dept],
            boxmean="sd",
            hovertemplate=f"<b>{dept}</b><br>Cost: $%{{y:,.2f}}<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Treatment Cost Distribution by Department",
        xaxis=dict(**_NO_GRID_AXIS, title="Department", tickangle=-30),
        yaxis=dict(**_GRID_AXIS, title="Treatment Cost ($)"),
        showlegend=False,
        height=420,
    )
    return fig


def plot_avg_cost_by_department(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar — average treatment cost per department."""
    stats = cost_by_department_stats(df)
    if stats.empty:
        return _empty_fig("Avg Treatment Cost by Department")

    stats_sorted = stats.sort_values("Mean_Cost", ascending=True)

    fig = go.Figure(go.Bar(
        x=stats_sorted["Mean_Cost"], y=stats_sorted["Department"],
        orientation="h",
        marker_color=_C_ACCENT,
        text=stats_sorted["Mean_Cost"].apply(lambda v: f"${v:,.0f}"),
        textposition="outside",
        customdata=stats_sorted[["Median_Cost","Patients","Total_Revenue"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Avg Cost: $%{x:,.2f}<br>"
            "Median Cost: $%{customdata[0]:,.2f}<br>"
            "Patients: %{customdata[1]:,}<br>"
            "Total Revenue: $%{customdata[2]:,.2f}<extra></extra>"
        ),
    ))
    height = max(300, len(stats_sorted) * 44 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Average Treatment Cost by Department",
        xaxis=dict(**_GRID_AXIS, title="Average Treatment Cost ($)",
                   range=[0, stats_sorted["Mean_Cost"].max() * 1.22]),
        yaxis=dict(**_NO_GRID_AXIS, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=80, t=55, b=40),
    )
    return fig


def plot_total_revenue_by_department(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar — total treatment revenue per department."""
    stats = cost_by_department_stats(df)
    if stats.empty:
        return _empty_fig("Total Revenue by Department")

    stats_sorted = stats.sort_values("Total_Revenue", ascending=True)

    fig = go.Figure(go.Bar(
        x=stats_sorted["Total_Revenue"], y=stats_sorted["Department"],
        orientation="h",
        marker_color=_C_PRIMARY,
        text=stats_sorted["Total_Revenue"].apply(lambda v: f"${v:,.0f}"),
        textposition="outside",
        customdata=stats_sorted[["Patients","Mean_Cost"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Total Revenue: $%{x:,.2f}<br>"
            "Patients: %{customdata[0]:,}<br>"
            "Avg Cost/Patient: $%{customdata[1]:,.2f}<extra></extra>"
        ),
    ))
    height = max(300, len(stats_sorted) * 44 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Total Treatment Revenue by Department",
        xaxis=dict(**_GRID_AXIS, title="Total Revenue ($)",
                   range=[0, stats_sorted["Total_Revenue"].max() * 1.22]),
        yaxis=dict(**_NO_GRID_AXIS, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=80, t=55, b=40),
    )
    return fig
