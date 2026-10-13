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
        4. Patient type only                       (if only type provided)
        5. Overall median                          (final fallback)

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
    # FIX: add patient-type-only level so type='Inpatient' without a dept
    # uses only inpatient records instead of silently falling to Overall.
    if patient_type:
        attempts.append((None, patient_type, None,
                         f"Patient Type ({patient_type})"))
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


# =============================================================================
# Feature 2 — Bed Demand Forecasting
# =============================================================================
# Method: Simple Exponential Smoothing (SES) on weekly inpatient arrivals,
#         combined with Feature 1 Expected LOS to estimate average bed demand.
#
# SES equation: S(t) = alpha × Y(t) + (1 − alpha) × S(t−1)
#   Y(t)     = observed inpatient count for period t
#   S(t−1)   = previous smoothed value
#   alpha    = smoothing parameter (0, 1]  — higher alpha → more weight on recent obs
#
# Alpha selection: grid search over [0.05, 0.95] step 0.05,
#   minimising MSE on the last ~20% of historical observations (chronological
#   holdout).  Future observations are never used to select alpha.
#
# Granularity: weekly aggregation.
#   Daily series has CV=1.71 and 4.4% zeros → noisier.
#   Weekly series has 52 observations, CV=1.12, 0 zero-weeks → better for SES.
#
# Bed demand approximation (steady-flow):
#   Average Beds ≈ Forecast_Daily_Arrivals × Expected_LOS_Days
#   This is valid when admission and discharge flows are reasonably stable.
#   It estimates *average* occupancy, not a daily peak or guaranteed capacity.
#
# Date semantics: confirmed — each patient row has a unique (ID, Date) pair;
#   multiple patients share the same calendar date, consistent with Date
#   being an admission/encounter date.
# =============================================================================

from config import COL_DATE, COL_LOS, COL_DEPT_NAME, COL_PATIENT_TYPE
INPATIENT_VALUE = "Inpatient"   # exact value in Patient type column
MIN_SERIES_OBS  = 8             # minimum weekly obs required to run SES


# ─────────────────────────────────────────────────────────────────────────────
# SES implementation (no external dependency on statsmodels)
# ─────────────────────────────────────────────────────────────────────────────

def _ses_smooth(series: np.ndarray, alpha: float) -> np.ndarray:
    """
    Apply Simple Exponential Smoothing to a 1-D array.

    S(0) = Y(0)
    S(t) = alpha × Y(t) + (1 − alpha) × S(t−1)

    Parameters
    ----------
    series : array of observed values (chronological)
    alpha  : smoothing parameter (0 < alpha ≤ 1)

    Returns
    -------
    np.ndarray of smoothed values, same length as series
    """
    n = len(series)
    s = np.empty(n)
    s[0] = series[0]
    for t in range(1, n):
        s[t] = alpha * series[t] + (1.0 - alpha) * s[t - 1]
    return s


def _ses_forecast(series: np.ndarray, alpha: float, horizon: int) -> np.ndarray:
    """
    Fit SES on the full series and project h steps ahead.

    For SES, all h-step-ahead forecasts equal the last smoothed value
    (the forecast function is flat/constant beyond the training window).

    Returns
    -------
    np.ndarray of length `horizon` — all values = last smoothed value
    """
    smoothed   = _ses_smooth(series, alpha)
    last_level = smoothed[-1]
    return np.full(horizon, last_level)


def _find_best_alpha(
    series: np.ndarray,
    alphas: np.ndarray | None = None,
) -> tuple[float, float, float]:
    """
    Grid-search for the alpha that minimises holdout MSE.

    Holdout = last max(4, n//5) observations (~20%).
    Alpha is chosen on the *training* portion only — no future leakage.

    Returns
    -------
    (best_alpha, holdout_mse, holdout_rmse)
    """
    if alphas is None:
        alphas = np.round(np.arange(0.05, 1.00, 0.05), 2)

    n         = len(series)
    hold_n    = max(4, n // 5)
    train     = series[: n - hold_n]
    test      = series[n - hold_n :]

    best_alpha = 0.3
    best_mse   = np.inf

    for alpha in alphas:
        fitted   = _ses_smooth(train, alpha)
        forecast = np.full(hold_n, fitted[-1])   # constant forecast
        mse      = float(np.mean((test - forecast) ** 2))
        if mse < best_mse:
            best_mse   = mse
            best_alpha = float(alpha)

    return best_alpha, best_mse, float(np.sqrt(best_mse))


# ─────────────────────────────────────────────────────────────────────────────
# Data preparation
# ─────────────────────────────────────────────────────────────────────────────

def build_weekly_inpatient_series(
    df: pd.DataFrame,
    department: str | None = None,
) -> pd.DataFrame:
    """
    Aggregate inpatient records into a weekly time series.

    Steps
    -----
    1. Select inpatient rows only (Patient type == 'Inpatient').
    2. Optionally filter to a single department.
    3. Group by (Year, Week) and count records.
    4. Sort chronologically.

    Uses the existing `Year` and `Week` derived columns added by the
    preprocessing pipeline.  Falls back to computing them if absent.

    Parameters
    ----------
    df         : processed (filtered) patient DataFrame
    department : if provided, restrict to that department

    Returns
    -------
    DataFrame with columns: Year, Week, Count — sorted chronologically.
    Returns empty DataFrame if insufficient inpatient records.
    """
    if COL_DATE not in df.columns or COL_PATIENT_TYPE not in df.columns:
        return pd.DataFrame()

    # Inpatient filter
    inp = df[df[COL_PATIENT_TYPE] == INPATIENT_VALUE].copy()

    # Department filter
    if department and COL_DEPT_NAME in inp.columns:
        inp = inp[inp[COL_DEPT_NAME] == department]

    if len(inp) == 0:
        return pd.DataFrame()

    # Ensure Year / Week columns exist
    if "Year" not in inp.columns:
        inp["Year"] = inp[COL_DATE].dt.year
    if "Week" not in inp.columns:
        inp["Week"] = inp[COL_DATE].dt.isocalendar().week.astype(int)

    weekly = (
        inp.groupby(["Year", "Week"])
        .size()
        .reset_index(name="Count")
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )
    return weekly


def validate_date_semantics(df: pd.DataFrame) -> dict:
    """
    Confirm that the Date column behaves like an admission/encounter date.

    Checks performed:
    - Column exists and is datetime
    - Zero nulls
    - Each (patient_id, date) pair is unique — patients are not double-counted
    - Multiple patients share the same date (i.e. it is not a single event date)

    Returns a dict with keys: valid (bool), notes (list[str])
    """
    from config import COL_PATIENT_ID
    notes = []
    valid = True

    if COL_DATE not in df.columns:
        return {"valid": False, "notes": ["Date column not found."]}

    if not pd.api.types.is_datetime64_any_dtype(df[COL_DATE]):
        valid = False
        notes.append("Date column is not datetime type.")

    null_count = int(df[COL_DATE].isna().sum())
    if null_count:
        notes.append(f"{null_count} null Date values found.")

    if COL_PATIENT_ID in df.columns:
        dupes = df.groupby([COL_PATIENT_ID, COL_DATE]).size()
        multi = int((dupes > 1).sum())
        if multi:
            valid = False
            notes.append(
                f"{multi} (patient_id, date) pairs appear more than once — "
                "Date may not be a unique admission date."
            )
        else:
            notes.append(
                "Each (patient_id, date) pair is unique — consistent with "
                "Date representing an admission or encounter date."
            )

    patients_per_date = df.groupby(COL_DATE).size()
    if patients_per_date.max() > 1:
        notes.append(
            f"Multiple patients share the same date (max {patients_per_date.max()} "
            "per day) — Date is a calendar date, not a single event."
        )

    unique_dates = int(df[COL_DATE].nunique())
    notes.append(
        f"Date range: {df[COL_DATE].min().date()} → {df[COL_DATE].max().date()} "
        f"({unique_dates} unique dates across {len(df):,} records)."
    )
    return {"valid": valid, "notes": notes}


# ─────────────────────────────────────────────────────────────────────────────
# Forecasting engine
# ─────────────────────────────────────────────────────────────────────────────

def run_ses_forecast(
    df: pd.DataFrame,
    department: str | None = None,
    horizon_weeks: int = 4,
) -> dict:
    """
    Full SES forecasting pipeline for inpatient weekly arrivals.

    Parameters
    ----------
    df             : processed (filtered) patient DataFrame
    department     : restrict to a single department if provided
    horizon_weeks  : number of weeks to forecast ahead

    Returns
    -------
    dict with keys:
        success          bool
        reason           str   — failure message when success=False
        weekly_df        DataFrame — historical weekly series
        alpha            float — optimised smoothing parameter
        holdout_rmse     float — RMSE on validation holdout
        holdout_n        int   — number of holdout weeks
        smoothed         np.ndarray — SES fitted values (in-sample)
        forecast         np.ndarray — forecast values (length = horizon_weeks)
        forecast_weekly  float — the forecast value per week (constant for SES)
        forecast_daily   float — forecast_weekly / 7
        n_obs            int   — number of historical weekly observations
    """
    weekly_df = build_weekly_inpatient_series(df, department)

    if weekly_df.empty or len(weekly_df) < MIN_SERIES_OBS:
        n = len(weekly_df)
        return {
            "success": False,
            "reason": (
                f"Insufficient inpatient data: {n} weekly observation(s) found "
                f"(minimum required: {MIN_SERIES_OBS}). "
                "Try a broader date range or department selection."
            ),
        }

    series = weekly_df["Count"].values.astype(float)
    alpha, hold_mse, hold_rmse = _find_best_alpha(series)
    smoothed = _ses_smooth(series, alpha)
    forecast = _ses_forecast(series, alpha, horizon_weeks)

    hold_n = max(4, len(series) // 5)
    n      = len(series)

    # Compute holdout MAE and baseline comparisons (no future leakage)
    train       = series[: n - hold_n]
    test        = series[n - hold_n :]
    ses_pred    = np.full(hold_n, _ses_smooth(train, alpha)[-1])
    hold_mae    = float(np.mean(np.abs(test - ses_pred)))

    # Naive baseline: last observed value
    naive_pred  = np.full(hold_n, series[n - hold_n - 1])
    naive_rmse  = float(np.sqrt(np.mean((test - naive_pred) ** 2)))
    naive_mae   = float(np.mean(np.abs(test - naive_pred)))

    # Historical mean baseline: mean of training window
    mean_pred   = np.full(hold_n, train.mean())
    mean_rmse   = float(np.sqrt(np.mean((test - mean_pred) ** 2)))
    mean_mae    = float(np.mean(np.abs(test - mean_pred)))

    return {
        "success":         True,
        "reason":          "",
        "weekly_df":       weekly_df,
        "alpha":           alpha,
        "holdout_rmse":    round(hold_rmse, 2),
        "holdout_mae":     round(hold_mae, 2),
        "holdout_n":       hold_n,
        "smoothed":        smoothed,
        "forecast":        forecast,
        "forecast_weekly": round(float(forecast[0]), 2),
        "forecast_daily":  round(float(forecast[0]) / 7.0, 4),
        "n_obs":           len(series),
        # Baseline comparisons
        "naive_rmse":      round(naive_rmse, 2),
        "naive_mae":       round(naive_mae, 2),
        "mean_rmse":       round(mean_rmse, 2),
        "mean_mae":        round(mean_mae, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bed demand calculation
# ─────────────────────────────────────────────────────────────────────────────

def estimate_bed_demand(
    forecast_daily: float,
    expected_los: float,
) -> dict:
    """
    Estimate average occupied beds using the steady-flow approximation.

    Formula:
        Average Bed Demand ≈ Forecast Daily Arrivals × Expected LOS (days)

    This is valid when admission and discharge rates are in approximate
    steady state. It represents average concurrent occupancy, NOT peak
    occupancy or exact daily census.

    Parameters
    ----------
    forecast_daily : daily inpatient arrivals from SES forecast
    expected_los   : historical median LOS for the relevant group

    Returns
    -------
    dict:
        avg_bed_demand   float — estimated average beds occupied
        formula          str   — human-readable formula used
        valid            bool  — False if either input is zero or negative
    """
    if forecast_daily <= 0 or expected_los <= 0:
        return {
            "avg_bed_demand": 0.0,
            "formula":        "N/A (zero or negative input)",
            "valid":          False,
        }

    avg_beds = round(forecast_daily * expected_los, 2)
    formula  = (
        f"{forecast_daily:.3f} arrivals/day × {expected_los:.2f} days LOS "
        f"= {avg_beds:.1f} beds"
    )
    return {
        "avg_bed_demand": avg_beds,
        "formula":        formula,
        "valid":          True,
    }


def department_bed_demand_table(
    df: pd.DataFrame,
    horizon_weeks: int = 4,
) -> pd.DataFrame:
    """
    Build a department-level bed demand comparison table.

    For each department with sufficient inpatient data:
    - Run SES to get forecast_daily
    - Fetch median Expected LOS via estimate_los
    - Compute estimated average bed demand

    Returns DataFrame with columns:
        Department, Records, Forecast_Daily, Expected_LOS, Avg_Bed_Demand,
        Sufficient_Data (bool)
    """
    if COL_DEPT_NAME not in df.columns:
        return pd.DataFrame()

    depts = sorted(df[df[COL_PATIENT_TYPE] == INPATIENT_VALUE][COL_DEPT_NAME]
                   .dropna().unique().tolist())
    rows = []
    for dept in depts:
        inp_count = int(
            ((df[COL_PATIENT_TYPE] == INPATIENT_VALUE) &
             (df[COL_DEPT_NAME] == dept)).sum()
        )
        res = run_ses_forecast(df, department=dept, horizon_weeks=horizon_weeks)
        los = estimate_los(df, dept, INPATIENT_VALUE, None)

        if res["success"] and not los["no_data"]:
            bd = estimate_bed_demand(res["forecast_daily"], los["expected_los"])
            rows.append({
                "Department":      dept,
                "Records":         inp_count,
                "Forecast_Daily":  res["forecast_daily"],
                "Expected_LOS":    los["expected_los"],
                "Avg_Bed_Demand":  bd["avg_bed_demand"],
                "Sufficient_Data": True,
            })
        else:
            rows.append({
                "Department":      dept,
                "Records":         inp_count,
                "Forecast_Daily":  None,
                "Expected_LOS":    los["expected_los"] if not los["no_data"] else None,
                "Avg_Bed_Demand":  None,
                "Sufficient_Data": False,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Chart functions — Bed Demand Forecasting
# ─────────────────────────────────────────────────────────────────────────────

def plot_ses_forecast(
    ses_result: dict,
    horizon_weeks: int,
    department_label: str = "All Departments",
) -> go.Figure:
    """
    Line chart: historical weekly inpatient arrivals + SES fitted line +
    forecast horizon with a shaded band.

    Clearly distinguishes:
      • Observed arrivals   (solid primary line)
      • SES fitted values   (dashed teal line)
      • Forecast           (dashed amber line, shaded band)
    """
    if not ses_result.get("success"):
        return _empty_fig(
            "Inpatient Arrival Forecast",
            ses_result.get("reason", "Insufficient data."),
        )

    weekly_df = ses_result["weekly_df"]
    smoothed  = ses_result["smoothed"]
    forecast  = ses_result["forecast"]
    alpha     = ses_result["alpha"]

    # Build x-axis labels: "W1 2007", "W2 2007", …
    hist_labels = [
        f"W{int(r.Week)} {int(r.Year)}" for r in weekly_df.itertuples()
    ]
    n_hist = len(hist_labels)

    # Forecast labels continue from the last historical week
    last_year = int(weekly_df["Year"].iloc[-1])
    last_week = int(weekly_df["Week"].iloc[-1])
    fc_labels = []
    w, y = last_week, last_year
    for _ in range(horizon_weeks):
        w += 1
        if w > 52:
            w, y = 1, y + 1
        fc_labels.append(f"W{w} {y}")

    all_labels = hist_labels + fc_labels

    # Forecast band (±1 RMSE)
    rmse       = ses_result["holdout_rmse"]
    fc_val     = ses_result["forecast_weekly"]
    fc_upper   = np.full(horizon_weeks, max(0, fc_val + rmse))
    fc_lower   = np.full(horizon_weeks, max(0, fc_val - rmse))

    fig = go.Figure()

    # 1. Observed arrivals
    fig.add_trace(go.Scatter(
        x=hist_labels,
        y=weekly_df["Count"].tolist(),
        mode="lines+markers",
        name="Observed (weekly)",
        line=dict(color=_C_PRIMARY, width=2),
        marker=dict(size=5, color=_C_PRIMARY),
        hovertemplate="<b>%{x}</b><br>Observed: %{y:.0f} inpatients<extra></extra>",
    ))

    # 2. SES fitted values
    fig.add_trace(go.Scatter(
        x=hist_labels,
        y=smoothed.tolist(),
        mode="lines",
        name=f"SES fitted (α={alpha:.2f})",
        line=dict(color=_C_TEAL, width=1.8, dash="dot"),
        hovertemplate="<b>%{x}</b><br>SES fitted: %{y:.1f}<extra></extra>",
    ))

    # 3. Forecast band (filled)
    fig.add_trace(go.Scatter(
        x=fc_labels + fc_labels[::-1],
        y=fc_upper.tolist() + fc_lower.tolist()[::-1],
        fill="toself",
        fillcolor="rgba(217,119,6,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
        name="Forecast band",
    ))

    # 4. Forecast line
    fig.add_trace(go.Scatter(
        x=fc_labels,
        y=forecast.tolist(),
        mode="lines+markers",
        name="Forecast",
        line=dict(color=_C_AMBER, width=2.2, dash="dash"),
        marker=dict(size=6, color=_C_AMBER, symbol="diamond"),
        hovertemplate="<b>%{x}</b><br>Forecast: %{y:.1f} inpatients/week<extra></extra>",
    ))

    # Vertical separator between history and forecast (categorical-safe)
    fig.add_shape(
        type="line",
        x0=hist_labels[-1], x1=hist_labels[-1],
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(dash="dot", color=_C_AXIS, width=1),
    )
    fig.add_annotation(
        x=hist_labels[-1], y=1.0,
        xref="x", yref="paper",
        text="← History | Forecast →",
        showarrow=False,
        font=dict(size=9, color=_C_AXIS),
        xanchor="left",
        yanchor="bottom",
        xshift=4,
    )

    layout = {k: v for k, v in _BASE_LAYOUT.items() if k not in ("margin", "legend")}
    fig.update_layout(
        **layout,
        title_text=f"Weekly Inpatient Arrivals & SES Forecast — {department_label}",
        xaxis=dict(
            **_NO_GRID,
            title="Week",
            tickvals=all_labels[::4],
            ticktext=all_labels[::4],
            tickangle=-35,
        ),
        yaxis=dict(**_GRID_AXIS, title="Inpatient Arrivals (per week)", rangemode="tozero"),
        legend=dict(
            orientation="h", y=1.1, x=0,
            font=dict(size=11, color=_C_TEXT),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=40, r=20, t=70, b=60),
        height=420,
    )
    return fig


def plot_bed_demand_bar(dept_table: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart of estimated average bed demand by department.
    Only departments with sufficient data are shown.
    """
    if dept_table.empty:
        return _empty_fig("Estimated Avg Bed Demand by Department")

    valid = dept_table.dropna(subset=["Avg_Bed_Demand"]).sort_values(
        "Avg_Bed_Demand", ascending=True
    )
    if valid.empty:
        return _empty_fig(
            "Estimated Avg Bed Demand by Department",
            "Insufficient data for all departments.",
        )

    fig = go.Figure(go.Bar(
        x=valid["Avg_Bed_Demand"],
        y=valid["Department"],
        orientation="h",
        marker_color=_C_TEAL,
        text=valid["Avg_Bed_Demand"].apply(lambda v: f"{v:.1f} beds"),
        textposition="outside",
        customdata=valid[["Forecast_Daily", "Expected_LOS", "Records"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Avg Bed Demand: %{x:.1f} beds<br>"
            "Forecast Daily Arrivals: %{customdata[0]:.3f}/day<br>"
            "Expected LOS: %{customdata[1]:.2f} days<br>"
            "Historical Records: %{customdata[2]:,}<extra></extra>"
        ),
    ))

    height = max(300, len(valid) * 50 + 80)
    layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **layout,
        title_text="Estimated Avg Bed Demand by Department",
        xaxis=dict(**_GRID_AXIS, title="Average Beds (estimated)",
                   range=[0, valid["Avg_Bed_Demand"].max() * 1.25]),
        yaxis=dict(**_NO_GRID, title="", automargin=True),
        height=height,
        margin=dict(l=10, r=80, t=55, b=40),
    )
    return fig


def plot_holdout_validation(ses_result: dict) -> go.Figure:
    """
    Actual vs predicted for the holdout validation period.
    Shows how well SES fitted on the training data predicted the held-out weeks.
    """
    if not ses_result.get("success"):
        return _empty_fig("Forecast Validation (Holdout)", ses_result.get("reason", ""))

    weekly_df = ses_result["weekly_df"]
    series    = weekly_df["Count"].values.astype(float)
    n         = len(series)
    hold_n    = ses_result["holdout_n"]
    alpha     = ses_result["alpha"]
    train     = series[: n - hold_n]
    test      = series[n - hold_n :]

    fitted_train = _ses_smooth(train, alpha)
    pred_hold    = np.full(hold_n, fitted_train[-1])

    hold_labels = [
        f"W{int(r.Week)} {int(r.Year)}"
        for r in weekly_df.tail(hold_n).itertuples()
    ]
    rmse = ses_result["holdout_rmse"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hold_labels, y=test.tolist(),
        mode="lines+markers", name="Actual",
        line=dict(color=_C_PRIMARY, width=2),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Actual: %{y:.0f} inpatients<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=hold_labels, y=pred_hold.tolist(),
        mode="lines+markers", name="SES Prediction",
        line=dict(color=_C_AMBER, width=2, dash="dash"),
        marker=dict(size=6, symbol="diamond"),
        hovertemplate="<b>%{x}</b><br>Predicted: %{y:.1f} inpatients<extra></extra>",
    ))

    layout = {k: v for k, v in _BASE_LAYOUT.items() if k not in ("margin", "legend")}
    fig.update_layout(
        **layout,
        title_text=f"Holdout Validation — Last {hold_n} Weeks (RMSE = {rmse:.2f})",
        xaxis=dict(**_NO_GRID, title="Week", tickangle=-30),
        yaxis=dict(**_GRID_AXIS, title="Inpatient Arrivals"),
        legend=dict(
            orientation="h", y=1.08, x=0,
            font=dict(size=11, color=_C_TEXT),
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=40, r=20, t=70, b=50),
    )
    return fig
