# =============================================================================
# utils/preprocessing.py — MediSight Preprocessing Pipeline
# =============================================================================
# Responsible for:
#   1. Cleaning column-name whitespace
#   2. Type conversion (dates, numerics)
#   3. Validation — flagging (not silently dropping) invalid records
#   4. Lookup enrichment — adding Department_Name via safe left-join
#   5. Runtime-derived features (date parts, operational flags)
#
# RULES
# -----
# - Never write anything back to the Excel file.
# - Never create CSV/Excel output files.
# - Invalid records are converted to NaN and counted, not silently removed.
# - Derived columns exist only in memory for the current session.
# =============================================================================

import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from config import (
    COL_STAFF_ID, COL_BED_ID, COL_DPT_ID, COL_PATIENT_ID,
    COL_NAME, COL_GENDER, COL_CITY, COL_STATE, COL_AGE,
    COL_PATIENT_TYPE, COL_STATUS, COL_TREATMENT_COST, COL_BED,
    COL_LOS, COL_ER_TIME, COL_DATE, COL_FEEDBACK, COL_RATING,
    COL_AGE_BUCKET, COL_CUSTOM, COL_FZ_ME, COL_DEPT_NAME, COL_DPT_ID,
    PROLONGED_STAY_THRESHOLD,
    AGE_MIN, AGE_MAX,
    TREATMENT_COST_MIN,
    LOS_MIN, LOS_MAX,
    ER_TIME_MIN, ER_TIME_MAX,
    RATING_MIN, RATING_MAX,
    STATUS_READMIT,
)


# ---------------------------------------------------------------------------
# Data-quality report
# ---------------------------------------------------------------------------

@dataclass
class QualityReport:
    """Holds transparent preprocessing metadata for display in the UI."""
    total_rows_raw: int = 0
    missing_by_column: dict = field(default_factory=dict)
    duplicate_row_count: int = 0
    invalid_dates: int = 0
    invalid_numeric: dict = field(default_factory=dict)   # col -> count
    records_nulled: dict = field(default_factory=dict)    # col -> count coerced to NaN
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1 — Column-name cleaning
# ---------------------------------------------------------------------------

def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from column names."""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Step 2 — Date conversion & validation
# ---------------------------------------------------------------------------

def _validate_dates(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    """
    Ensure the Date column is datetime.
    Records that cannot be parsed are coerced to NaT and counted.
    """
    df = df.copy()
    if COL_DATE not in df.columns:
        report.notes.append(f"Column '{COL_DATE}' not found — skipping date validation.")
        return df

    original = df[COL_DATE].copy()
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
    invalid = df[COL_DATE].isna() & original.notna()
    count = int(invalid.sum())
    report.invalid_dates = count
    if count:
        report.notes.append(
            f"{count} rows had unparseable dates → coerced to NaT."
        )
    return df


# ---------------------------------------------------------------------------
# Step 3 — Numeric conversion & range validation
# ---------------------------------------------------------------------------

def _to_numeric_validated(
    df: pd.DataFrame,
    col: str,
    min_val: float | None,
    max_val: float | None,
    report: QualityReport,
) -> pd.DataFrame:
    """
    Coerce column to numeric. Values outside [min_val, max_val] are set to NaN.
    All counts are recorded in the QualityReport.
    """
    df = df.copy()
    if col not in df.columns:
        return df

    before_nulls = int(df[col].isna().sum())
    df[col] = pd.to_numeric(df[col], errors="coerce")
    after_nulls = int(df[col].isna().sum())
    newly_nulled = after_nulls - before_nulls

    if newly_nulled:
        report.records_nulled[col] = report.records_nulled.get(col, 0) + newly_nulled
        report.invalid_numeric[col] = report.invalid_numeric.get(col, 0) + newly_nulled

    # Range check
    if min_val is not None:
        out_of_range = df[col].notna() & (df[col] < min_val)
        count = int(out_of_range.sum())
        if count:
            df.loc[out_of_range, col] = np.nan
            report.records_nulled[col] = report.records_nulled.get(col, 0) + count
            report.invalid_numeric[col] = report.invalid_numeric.get(col, 0) + count
            report.notes.append(
                f"{count} rows in '{col}' below minimum ({min_val}) → set to NaN."
            )

    if max_val is not None:
        out_of_range = df[col].notna() & (df[col] > max_val)
        count = int(out_of_range.sum())
        if count:
            df.loc[out_of_range, col] = np.nan
            report.records_nulled[col] = report.records_nulled.get(col, 0) + count
            report.invalid_numeric[col] = report.invalid_numeric.get(col, 0) + count
            report.notes.append(
                f"{count} rows in '{col}' above maximum ({max_val}) → set to NaN."
            )

    return df


def _validate_numerics(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    """Apply numeric validation to all numeric patient columns."""
    df = _to_numeric_validated(df, COL_AGE,            AGE_MIN,            AGE_MAX,            report)
    df = _to_numeric_validated(df, COL_TREATMENT_COST, TREATMENT_COST_MIN, None,               report)
    df = _to_numeric_validated(df, COL_LOS,            LOS_MIN,            LOS_MAX,            report)
    df = _to_numeric_validated(df, COL_ER_TIME,        ER_TIME_MIN,        ER_TIME_MAX,        report)
    df = _to_numeric_validated(df, COL_RATING,         RATING_MIN,         RATING_MAX,         report)
    return df


# ---------------------------------------------------------------------------
# Step 4 — Empty string normalisation
# ---------------------------------------------------------------------------

def _normalise_empty_strings(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    """
    Replace empty strings and strings containing only whitespace with NaN
    across all string columns so .isna() checks work consistently.
    """
    df = df.copy()
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in str_cols:
        mask = df[col].astype(str).str.strip() == ""
        count = int(mask.sum())
        if count:
            df.loc[mask, col] = np.nan
            report.notes.append(
                f"{count} empty string(s) in '{col}' → set to NaN."
            )
    return df


# ---------------------------------------------------------------------------
# Step 5 — Duplicate detection
# ---------------------------------------------------------------------------

def _check_duplicates(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    """
    Identify and count fully duplicate rows.
    Duplicates are kept (not dropped) — count is recorded for the UI.
    """
    report.duplicate_row_count = int(df.duplicated().sum())
    if report.duplicate_row_count:
        report.notes.append(
            f"{report.duplicate_row_count} fully duplicate rows detected (retained)."
        )
    return df


# ---------------------------------------------------------------------------
# Step 6 — Missing value audit
# ---------------------------------------------------------------------------

def _audit_missing(df: pd.DataFrame, report: QualityReport) -> None:
    """Populate report.missing_by_column with current null counts."""
    report.missing_by_column = {
        col: int(df[col].isna().sum())
        for col in df.columns
        if df[col].isna().any()
    }


# ---------------------------------------------------------------------------
# Step 7 — Department enrichment (safe left-join)
# ---------------------------------------------------------------------------

def _enrich_with_department(
    patient_df: pd.DataFrame,
    dept_df: pd.DataFrame,
    report: QualityReport,
) -> pd.DataFrame:
    """
    Add Department_Name to the patient DataFrame via a left-join on Dpt_ID.

    Safety checks performed before merging:
    - dept_df must have unique Dpt_ID values (prevents row multiplication).
    - Row count must not change after the merge.

    If any check fails, the enrichment is skipped and documented.
    """
    if COL_DPT_ID not in patient_df.columns or COL_DPT_ID not in dept_df.columns:
        report.notes.append(
            "Department enrichment skipped: Dpt_ID not present in both tables."
        )
        return patient_df

    if dept_df[COL_DPT_ID].duplicated().any():
        report.notes.append(
            "Department enrichment skipped: Dpt_ID is not unique in Department table "
            "— merge would multiply patient rows."
        )
        return patient_df

    if dept_df[COL_DPT_ID].isna().any():
        report.notes.append(
            "Department enrichment skipped: null Dpt_ID values found in Department table."
        )
        return patient_df

    rows_before = len(patient_df)
    merged = patient_df.merge(
        dept_df[[COL_DPT_ID, COL_DEPT_NAME]],
        on=COL_DPT_ID,
        how="left",
    )

    if len(merged) != rows_before:
        report.notes.append(
            f"Department enrichment aborted: merge increased rows "
            f"({rows_before} → {len(merged)}). Left-join preserved original rows."
        )
        return patient_df

    unmatched = int(merged[COL_DEPT_NAME].isna().sum())
    if unmatched:
        report.notes.append(
            f"{unmatched} patient records had no matching Department_Name."
        )
    else:
        report.notes.append(
            "Department_Name successfully added to all patient records."
        )

    return merged


# ---------------------------------------------------------------------------
# Step 8 — Derived features
# ---------------------------------------------------------------------------

def _add_derived_features(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    """
    Create runtime-only derived columns.
    These are never written back to the Excel file.

    Date-based features  : Year, Month, Month_Name, Week, Quarter, Day, Day_Name
    Operational features : Occupied_Bed_Flag, Readmission_Flag, Prolonged_Stay
    """
    df = df.copy()

    # --- Date features ---
    if COL_DATE in df.columns and pd.api.types.is_datetime64_any_dtype(df[COL_DATE]):
        df["Year"]       = df[COL_DATE].dt.year
        df["Month"]      = df[COL_DATE].dt.month
        df["Month_Name"] = df[COL_DATE].dt.strftime("%B")
        df["Week"]       = df[COL_DATE].dt.isocalendar().week.astype("Int64")
        df["Quarter"]    = df[COL_DATE].dt.quarter
        df["Day"]        = df[COL_DATE].dt.day
        df["Day_Name"]   = df[COL_DATE].dt.strftime("%A")
        report.notes.append(
            "Date-based derived features added: Year, Month, Month_Name, Week, Quarter, Day, Day_Name."
        )
    else:
        report.notes.append(
            "Date-based derived features skipped: Date column not available as datetime."
        )

    # --- Occupied_Bed_Flag ---
    # A patient record has an occupied bed when Bed_ID is not null.
    if COL_BED_ID in df.columns:
        df["Occupied_Bed_Flag"] = df[COL_BED_ID].notna().astype(int)
        report.notes.append(
            "Occupied_Bed_Flag derived: 1 where Bed_ID is present, 0 otherwise."
        )

    # --- Readmission_Flag ---
    # Determined by the actual Status value for readmission (STATUS_READMIT = "Readmit").
    if COL_STATUS in df.columns:
        df["Readmission_Flag"] = (df[COL_STATUS] == STATUS_READMIT).astype(int)
        report.notes.append(
            f"Readmission_Flag derived: 1 where Status == '{STATUS_READMIT}'."
        )

    # --- Prolonged_Stay ---
    # Uses the configurable threshold from config.py.
    if COL_LOS in df.columns and pd.api.types.is_numeric_dtype(df[COL_LOS]):
        df["Prolonged_Stay"] = (df[COL_LOS] > PROLONGED_STAY_THRESHOLD).astype(int)
        report.notes.append(
            f"Prolonged_Stay derived: 1 where LOS > {PROLONGED_STAY_THRESHOLD} days."
        )

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_patient_data(
    patient_df: pd.DataFrame,
    dept_df: pd.DataFrame,
) -> tuple[pd.DataFrame, QualityReport]:
    """
    Full preprocessing pipeline for the patient dataset.

    Parameters
    ----------
    patient_df : raw patient DataFrame from data_loader
    dept_df    : raw department DataFrame from data_loader (used for enrichment)

    Returns
    -------
    (processed_df, report)
        processed_df : cleaned, enriched, and feature-extended DataFrame
        report       : QualityReport instance for display in the Data Quality panel
    """
    report = QualityReport()
    report.total_rows_raw = len(patient_df)

    df = _clean_column_names(patient_df)
    dept_df_clean = _clean_column_names(dept_df)

    df = _normalise_empty_strings(df, report)
    df = _validate_dates(df, report)
    df = _validate_numerics(df, report)
    df = _check_duplicates(df, report)
    _audit_missing(df, report)

    df = _enrich_with_department(df, dept_df_clean, report)
    df = _add_derived_features(df, report)

    return df, report


def preprocess_staff_data(staff_df: pd.DataFrame) -> pd.DataFrame:
    """
    Light preprocessing for Staff_Detail.
    Strips column whitespace; no heavy transformation needed.
    """
    df = _clean_column_names(staff_df)
    return df


def preprocess_department_data(dept_df: pd.DataFrame) -> pd.DataFrame:
    """
    Light preprocessing for Department.
    Strips column whitespace; no transformation needed.
    """
    df = _clean_column_names(dept_df)
    return df


def preprocess_bed_data(bed_df: pd.DataFrame) -> pd.DataFrame:
    """
    Light preprocessing for Bed_Detail.
    Strips column whitespace; no transformation needed.
    """
    df = _clean_column_names(bed_df)
    return df
