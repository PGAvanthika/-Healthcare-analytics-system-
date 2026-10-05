# =============================================================================
# utils/metrics.py — MediSight KPI Engine
# =============================================================================
# All KPI values are calculated dynamically from the DataFrames passed in.
# No values are hardcoded.
#
# ARCHITECTURE
# ------------
# calculate_kpis(df, staff_df, bed_df) is the primary function.
# It accepts a *filtered* patient DataFrame so KPIs update automatically
# when Streamlit filters change without any logic changes here.
#
# Staff and bed KPIs are calculated from their own dimension tables
# (not derived from the patient DataFrame alone) so they remain accurate.
# =============================================================================

import pandas as pd
import numpy as np
from dataclasses import dataclass

from config import (
    COL_PATIENT_ID,
    COL_PATIENT_TYPE,
    COL_STATUS,
    COL_TREATMENT_COST,
    COL_LOS,
    COL_ER_TIME,
    COL_RATING,
    COL_BED_ID,
    COL_STAFF_ID,
    STATUS_DEATH,
    STATUS_DISCHARGE,
    STATUS_READMIT,
    PATIENT_TYPE_INPATIENT,
    PATIENT_TYPE_OUTPATIENT,
)


# ---------------------------------------------------------------------------
# KPI result container
# ---------------------------------------------------------------------------

@dataclass
class KPIResult:
    """
    Holds all 13 computed KPIs.
    Using a dataclass keeps the return value explicit and easy to extend.
    """
    total_patients: int        = 0
    inpatients: int            = 0
    outpatients: int           = 0
    total_staff: int           = 0
    recorded_occupied_beds: int = 0
    avg_los: float             = 0.0
    avg_er_time: float         = 0.0
    avg_treatment_cost: float  = 0.0
    total_revenue: float       = 0.0
    deaths: int                = 0
    discharges: int            = 0
    readmissions: int          = 0
    avg_rating: float          = 0.0


# ---------------------------------------------------------------------------
# Individual KPI helpers
# ---------------------------------------------------------------------------

def _total_patients(df: pd.DataFrame) -> int:
    """
    Count unique patient IDs in the filtered DataFrame.
    ID values are verified to be unique in the full dataset (2506 unique IDs
    across 2506 rows), so len(df) would also be valid.
    Using nunique() makes the intent explicit and guards against edge cases.
    """
    if COL_PATIENT_ID not in df.columns:
        return 0
    return int(df[COL_PATIENT_ID].nunique())


def _inpatients(df: pd.DataFrame) -> int:
    """Count rows where Patient type == 'Inpatient'."""
    if COL_PATIENT_TYPE not in df.columns:
        return 0
    return int((df[COL_PATIENT_TYPE] == PATIENT_TYPE_INPATIENT).sum())


def _outpatients(df: pd.DataFrame) -> int:
    """
    Count rows where Patient type == 'outpatient'.
    Note: the source data uses lowercase 'outpatient' — preserved as-is.
    """
    if COL_PATIENT_TYPE not in df.columns:
        return 0
    return int((df[COL_PATIENT_TYPE] == PATIENT_TYPE_OUTPATIENT).sum())


def _total_staff(staff_df: pd.DataFrame) -> int:
    """
    Count unique staff members from the Staff_Detail dimension table.
    The table has 262 rows, each representing one unique staff member.
    Using nunique() on Staff_Id is explicit and safe.
    """
    if COL_STAFF_ID not in staff_df.columns:
        return 0
    return int(staff_df[COL_STAFF_ID].nunique())


def _recorded_occupied_beds(df: pd.DataFrame, bed_df: pd.DataFrame) -> int:
    """
    Count unique Bed_IDs referenced in the filtered patient DataFrame.

    This metric is correctly labelled 'Recorded Occupied Beds' because
    the data represents bed assignment records, not a live snapshot.

    The Bed_Detail table has 2847 total bed records.
    The patient dataset has 1751 non-null Bed_ID values (755 patients
    have no bed assigned — typically outpatients or non-admitted cases).
    """
    if COL_BED_ID not in df.columns:
        return 0
    return int(df[COL_BED_ID].dropna().nunique())


def _avg_los(df: pd.DataFrame) -> float:
    """
    Mean of valid LOS (Length of Stay) values in days.
    NaN values (invalid or missing) are excluded by .mean() automatically.
    """
    if COL_LOS not in df.columns:
        return 0.0
    val = df[COL_LOS].mean()
    return round(float(val), 2) if not pd.isna(val) else 0.0


def _avg_er_time(df: pd.DataFrame) -> float:
    """
    Mean of valid ER_Time values (minutes in A&E / emergency room).
    719 rows have no ER_Time — these are excluded automatically by .mean().
    """
    if COL_ER_TIME not in df.columns:
        return 0.0
    val = df[COL_ER_TIME].mean()
    return round(float(val), 2) if not pd.isna(val) else 0.0


def _avg_treatment_cost(df: pd.DataFrame) -> float:
    """
    Mean of valid treatemencost values.
    treatemencost represents a per-patient monetary cost (range: 2.54–1241.33).
    """
    if COL_TREATMENT_COST not in df.columns:
        return 0.0
    val = df[COL_TREATMENT_COST].mean()
    return round(float(val), 2) if not pd.isna(val) else 0.0


def _total_revenue(df: pd.DataFrame) -> float:
    """
    Sum of treatemencost across all filtered patient records.
    This represents total treatment revenue because treatemencost is a
    per-patient monetary amount (confirmed from data inspection).
    """
    if COL_TREATMENT_COST not in df.columns:
        return 0.0
    val = df[COL_TREATMENT_COST].sum()
    return round(float(val), 2) if not pd.isna(val) else 0.0


def _deaths(df: pd.DataFrame) -> int:
    """Count records where Status == 'Death' (actual value confirmed from workbook)."""
    if COL_STATUS not in df.columns:
        return 0
    return int((df[COL_STATUS] == STATUS_DEATH).sum())


def _discharges(df: pd.DataFrame) -> int:
    """Count records where Status == 'Discharge'."""
    if COL_STATUS not in df.columns:
        return 0
    return int((df[COL_STATUS] == STATUS_DISCHARGE).sum())


def _readmissions(df: pd.DataFrame) -> int:
    """Count records where Status == 'Readmit'."""
    if COL_STATUS not in df.columns:
        return 0
    return int((df[COL_STATUS] == STATUS_READMIT).sum())


def _avg_rating(df: pd.DataFrame) -> float:
    """
    Mean of valid Rating values (scale 1–5).
    All 2506 rows have a rating; no NaN expected unless range validation
    nulled any out-of-range values.
    """
    if COL_RATING not in df.columns:
        return 0.0
    val = df[COL_RATING].mean()
    return round(float(val), 2) if not pd.isna(val) else 0.0


# ---------------------------------------------------------------------------
# Staff metrics
# ---------------------------------------------------------------------------

def calculate_staff_metrics(staff_df: pd.DataFrame) -> dict:
    """
    Return a summary of staff-related metrics.
    Kept separate from calculate_kpis so it can be called independently.
    """
    return {
        "total_staff": _total_staff(staff_df),
    }


# ---------------------------------------------------------------------------
# Bed metrics
# ---------------------------------------------------------------------------

def calculate_bed_metrics(df: pd.DataFrame, bed_df: pd.DataFrame) -> dict:
    """
    Return a summary of bed-related metrics.

    Notes
    -----
    - Total beds in Bed_Detail: 2847
    - Recorded occupied beds: unique Bed_IDs referenced in patient records
    - This does NOT represent live occupancy; it represents historical records.
    """
    total_beds = int(len(bed_df)) if bed_df is not None else 0
    occupied   = _recorded_occupied_beds(df, bed_df)
    return {
        "total_beds_in_detail": total_beds,
        "recorded_occupied_beds": occupied,
    }


# ---------------------------------------------------------------------------
# Primary KPI engine
# ---------------------------------------------------------------------------

def calculate_kpis(
    df: pd.DataFrame,
    staff_df: pd.DataFrame,
    bed_df: pd.DataFrame,
) -> KPIResult:
    """
    Calculate all 13 KPIs from the provided DataFrames.

    Parameters
    ----------
    df        : Patient DataFrame — may be filtered (date range, dept, etc.).
                The function makes no assumptions about which rows are present.
    staff_df  : Staff_Detail DataFrame — used for Total Staff count.
                Staff count is NOT filtered with patient filters because
                staff members exist independent of the patient filter window.
    bed_df    : Bed_Detail DataFrame — used for total bed context.

    Returns
    -------
    KPIResult dataclass with all 13 computed values.

    Usage
    -----
    # Unfiltered
    kpis = calculate_kpis(processed_df, staff_df, bed_df)

    # Filtered
    filtered_df = processed_df[processed_df["Department_Name"] == "Cardiology"]
    kpis = calculate_kpis(filtered_df, staff_df, bed_df)
    """
    if df is None or len(df) == 0:
        return KPIResult()

    return KPIResult(
        total_patients        = _total_patients(df),
        inpatients            = _inpatients(df),
        outpatients           = _outpatients(df),
        total_staff           = _total_staff(staff_df),
        recorded_occupied_beds = _recorded_occupied_beds(df, bed_df),
        avg_los               = _avg_los(df),
        avg_er_time           = _avg_er_time(df),
        avg_treatment_cost    = _avg_treatment_cost(df),
        total_revenue         = _total_revenue(df),
        deaths                = _deaths(df),
        discharges            = _discharges(df),
        readmissions          = _readmissions(df),
        avg_rating            = _avg_rating(df),
    )
