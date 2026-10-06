# =============================================================================
# utils/descriptive.py — MediSight Phase 1 Overview Charts
# =============================================================================
# Five reusable Plotly chart functions for the Phase 1 dashboard.
# Each function:
#   - Accepts the *already filtered* patient DataFrame as its only data source.
#   - Returns a plotly.graph_objects.Figure.
#   - Performs only in-memory aggregations — no file I/O, no new datasets.
#
# Color palette and layout theme are kept consistent across all charts.
# Charts are designed to work at any filtered slice of the data.
# =============================================================================

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config import (
    COL_PATIENT_TYPE,
    COL_STATUS,
    COL_DEPT_NAME,
    COL_AGE_BUCKET,
)

# ---------------------------------------------------------------------------
# Shared theme  — healthcare palette
# ---------------------------------------------------------------------------
# Tokens mirror the design constants in app.py so charts match the UI.
_C_BG      = "#FFFFFF"   # white chart background
_C_GRID    = "#EEF2F7"   # subtle grid lines
_C_AXIS    = "#64748B"   # axis line colour
_C_TEXT    = "#17324D"   # axis label / annotation text
_C_TITLE   = "#123B5D"   # chart title

# Base Plotly layout applied to every chart for visual consistency.
_BASE_LAYOUT = dict(
    paper_bgcolor=_C_BG,
    plot_bgcolor=_C_BG,
    font=dict(family="'Segoe UI', sans-serif", size=12, color=_C_TEXT),
    title_font=dict(size=14, color=_C_TITLE, family="'Segoe UI', sans-serif"),
    margin=dict(l=40, r=20, t=50, b=40),
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

# Colour tokens
_DONUT_COLOURS = ["#123B5D", "#2A9D8F"]   # primary + accent
_BAR_COLOUR    = "#0F766E"                 # teal
_STATUS_COLOURS = {
    "Normal":    "#0F766E",   # teal
    "Discharge": "#2A9D8F",   # accent
    "Readmit":   "#E2A03F",   # amber
    "ICU":       "#D97706",   # orange
    "Death":     "#B91C1C",   # red
}
_DEPT_COLOUR = "#123B5D"   # primary
_LINE_COLOUR = "#0F766E"   # teal
_AGE_COLOUR  = "#2A9D8F"   # accent

# Logical age-bucket order (not alphabetical)
_AGE_ORDER = ["Below 6Y", "6-20Y", "21-40Y", "41-60y", "60+Y"]


# ---------------------------------------------------------------------------
# Chart 1 — Patient Type Distribution (Donut)
# ---------------------------------------------------------------------------

def plot_patient_type_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart showing Inpatient vs Outpatient split.

    Parameters
    ----------
    df : filtered patient DataFrame

    Returns
    -------
    plotly Figure
    """
    if COL_PATIENT_TYPE not in df.columns or len(df) == 0:
        return _empty_figure("Patient Type Distribution", "No data for current filter.")

    counts = df[COL_PATIENT_TYPE].value_counts().reset_index()
    counts.columns = ["Patient Type", "Count"]

    fig = go.Figure(
        go.Pie(
            labels=counts["Patient Type"],
            values=counts["Count"],
            hole=0.45,
            marker=dict(colors=_DONUT_COLOURS, line=dict(color="#ffffff", width=2)),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Patients: %{value:,}<br>Share: %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Patient Type Distribution",
        showlegend=True,
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 2 — Patient Status Distribution (Vertical Bar)
# ---------------------------------------------------------------------------

def plot_status_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Vertical bar chart of patient counts by Status, sorted descending.

    Parameters
    ----------
    df : filtered patient DataFrame

    Returns
    -------
    plotly Figure
    """
    if COL_STATUS not in df.columns or len(df) == 0:
        return _empty_figure("Patient Status Distribution", "No data for current filter.")

    counts = (
        df[COL_STATUS]
        .value_counts()
        .reset_index()
    )
    counts.columns = ["Status", "Count"]
    counts = counts.sort_values("Count", ascending=False)

    colours = [_STATUS_COLOURS.get(s, _BAR_COLOUR) for s in counts["Status"]]

    fig = go.Figure(
        go.Bar(
            x=counts["Status"],
            y=counts["Count"],
            marker_color=colours,
            text=counts["Count"],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Patients: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Patient Status Distribution",
        xaxis=dict(title="Status", showgrid=False, linecolor=_C_AXIS,
                   tickfont=dict(color=_C_TEXT), title_font=dict(color=_C_TEXT)),
        yaxis=dict(title="Patient Count", showgrid=True, gridcolor=_C_GRID,
                   linecolor=_C_AXIS, tickfont=dict(color=_C_TEXT),
                   title_font=dict(color=_C_TEXT)),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 3 — Patients by Department (Horizontal Bar)
# ---------------------------------------------------------------------------

def plot_department_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart of patient counts per department, sorted descending.
    Uses Department_Name added by the existing preprocessing enrichment.
    No additional merge is performed here.

    Parameters
    ----------
    df : filtered patient DataFrame (must already contain Department_Name)

    Returns
    -------
    plotly Figure
    """
    if COL_DEPT_NAME not in df.columns or len(df) == 0:
        return _empty_figure("Patients by Department", "Department data not available.")

    counts = (
        df[COL_DEPT_NAME]
        .value_counts()
        .reset_index()
    )
    counts.columns = ["Department", "Count"]
    counts = counts.sort_values("Count", ascending=True)   # ascending=True → largest at top in horizontal bar

    fig = go.Figure(
        go.Bar(
            x=counts["Count"],
            y=counts["Department"],
            orientation="h",
            marker_color=_DEPT_COLOUR,
            text=counts["Count"],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Patients: %{x:,}<extra></extra>",
        )
    )

    # Dynamic height: at least 300px, 40px per department bar
    chart_height = max(300, len(counts) * 42 + 80)

    dept_layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "margin"}
    fig.update_layout(
        **dept_layout,
        title_text="Patients by Department",
        xaxis=dict(title="Patient Count", showgrid=True, gridcolor=_C_GRID,
                   linecolor=_C_AXIS, tickfont=dict(color=_C_TEXT),
                   title_font=dict(color=_C_TEXT)),
        yaxis=dict(title="", showgrid=False, linecolor=_C_AXIS,
                   tickfont=dict(color=_C_TEXT), automargin=True),
        height=chart_height,
        margin=dict(l=10, r=60, t=50, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 4 — Monthly Patient Volume (Line)
# ---------------------------------------------------------------------------

def plot_monthly_patient_volume(df: pd.DataFrame) -> go.Figure:
    """
    Line chart of patient count grouped by calendar month.
    Uses the existing derived Year / Month / Month_Name columns.
    Months are always displayed in chronological order (Jan→Dec).

    Parameters
    ----------
    df : filtered patient DataFrame (must contain Year, Month, Month_Name)

    Returns
    -------
    plotly Figure
    """
    required = {"Year", "Month", "Month_Name"}
    if not required.issubset(df.columns) or len(df) == 0:
        return _empty_figure("Monthly Patient Volume", "Date-derived columns not available.")

    monthly = (
        df.groupby(["Year", "Month", "Month_Name"], observed=True)
        .size()
        .reset_index(name="Count")
        .sort_values(["Year", "Month"])   # chronological order guaranteed
    )

    # Build a display label: "Jan 2007" — works correctly across multi-year data too
    monthly["Label"] = monthly["Month_Name"].str[:3] + " " + monthly["Year"].astype(str)

    fig = go.Figure(
        go.Scatter(
            x=monthly["Label"],
            y=monthly["Count"],
            mode="lines+markers",
            line=dict(color=_LINE_COLOUR, width=2.5),
            marker=dict(color=_LINE_COLOUR, size=7, symbol="circle"),
            fill="tozeroy",
            fillcolor="rgba(15,118,110,0.08)",
            hovertemplate="<b>%{x}</b><br>Patients: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Monthly Patient Volume",
        xaxis=dict(
            title="Month", showgrid=False, linecolor=_C_AXIS,
            tickangle=-30, categoryorder="trace",
            tickfont=dict(color=_C_TEXT), title_font=dict(color=_C_TEXT),
        ),
        yaxis=dict(title="Patient Count", showgrid=True, gridcolor=_C_GRID,
                   linecolor=_C_AXIS, tickfont=dict(color=_C_TEXT),
                   title_font=dict(color=_C_TEXT)),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 5 — Age Bucket Distribution (Vertical Bar)
# ---------------------------------------------------------------------------

def plot_age_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Vertical bar chart of patient counts by Age Bucket.
    Buckets are displayed in logical age order, not alphabetically.

    Parameters
    ----------
    df : filtered patient DataFrame

    Returns
    -------
    plotly Figure
    """
    if COL_AGE_BUCKET not in df.columns or len(df) == 0:
        return _empty_figure("Patient Age Distribution", "Age Bucket data not available.")

    counts = df[COL_AGE_BUCKET].value_counts().reset_index()
    counts.columns = ["Age Bucket", "Count"]

    # Apply logical order — only include buckets present in the filtered data
    order = [b for b in _AGE_ORDER if b in counts["Age Bucket"].values]
    counts["Age Bucket"] = pd.Categorical(counts["Age Bucket"], categories=order, ordered=True)
    counts = counts.sort_values("Age Bucket")

    fig = go.Figure(
        go.Bar(
            x=counts["Age Bucket"].astype(str),
            y=counts["Count"],
            marker_color=_AGE_COLOUR,
            text=counts["Count"],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Patients: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text="Patient Age Distribution",
        xaxis=dict(title="Age Group", showgrid=False, linecolor=_C_AXIS,
                   tickfont=dict(color=_C_TEXT), title_font=dict(color=_C_TEXT)),
        yaxis=dict(title="Patient Count", showgrid=True, gridcolor=_C_GRID,
                   linecolor=_C_AXIS, tickfont=dict(color=_C_TEXT),
                   title_font=dict(color=_C_TEXT)),
    )
    return fig


# ---------------------------------------------------------------------------
# Internal helper — empty state figure
# ---------------------------------------------------------------------------

def _empty_figure(title: str, message: str) -> go.Figure:
    """Return a blank figure with a centred message when no data is available."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=13, color="#7f8c8d"),
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_text=title,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
