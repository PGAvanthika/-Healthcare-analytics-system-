# =============================================================================
# utils/data_loader.py — MediSight Data Loading Layer
# =============================================================================
# Responsible ONLY for reading data from the Excel workbook.
# No transformation, no derived features, no KPI logic here.
#
# All functions use @st.cache_data so Streamlit does not re-read the file
# on every UI interaction.
#
# The DATA_PATH from config.py is resolved relative to the project root
# (the directory that contains app.py), keeping the app fully portable.
# =============================================================================

import os
import streamlit as st
import pandas as pd

from config import (
    DATA_PATH,
    SHEET_PATIENT,
    SHEET_STAFF,
    SHEET_DEPARTMENT,
    SHEET_BED,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_data_path() -> str:
    """
    Return an absolute path to the Excel file regardless of the working
    directory the process was started from.

    Streamlit is typically launched from the project root, so DATA_PATH
    (a relative path like "data/Hospital ...xlsx") resolves correctly.
    As a fallback, we also try resolving relative to this file's location.
    """
    # Try the path as-is (works when cwd == project root)
    if os.path.exists(DATA_PATH):
        return DATA_PATH

    # Fallback: resolve relative to the utils/ package directory → go up one level
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    candidate = os.path.join(project_root, DATA_PATH)
    if os.path.exists(candidate):
        return candidate

    # Return the original path; the caller will handle the FileNotFoundError
    return DATA_PATH


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading workbook…")
def load_workbook() -> dict[str, pd.DataFrame]:
    """
    Read every sheet from the Excel workbook and return a dict
    keyed by sheet name.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys are the exact sheet names from the workbook.

    Raises
    ------
    FileNotFoundError
        If the Excel file cannot be located.
    """
    path = _resolve_data_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at '{path}'. "
            "Please place 'Hospital  Health Care Management Data set.xlsx' "
            "inside the data/ directory."
        )

    xl = pd.ExcelFile(path, engine="openpyxl")
    sheets: dict[str, pd.DataFrame] = {}
    for name in xl.sheet_names:
        sheets[name] = xl.parse(name)
    return sheets


@st.cache_data(show_spinner="Loading patient data…")
def load_patient_data() -> pd.DataFrame:
    """
    Load the main patient dataset (sheet: 'Detail data dataset').

    Returns the raw DataFrame exactly as it appears in the workbook —
    no cleaning, no type coercion, no derived columns.
    Preprocessing is the responsibility of utils/preprocessing.py.
    """
    path = _resolve_data_path()
    return pd.read_excel(path, sheet_name=SHEET_PATIENT, engine="openpyxl")


@st.cache_data(show_spinner="Loading staff data…")
def load_staff_data() -> pd.DataFrame:
    """
    Load the Staff_Detail sheet.

    Columns: Staff_Id (int), Staff Name (str)
    Rows: 262 — one row per unique staff member.
    """
    path = _resolve_data_path()
    return pd.read_excel(path, sheet_name=SHEET_STAFF, engine="openpyxl")


@st.cache_data(show_spinner="Loading department data…")
def load_department_data() -> pd.DataFrame:
    """
    Load the Department sheet.

    Columns: Dpt_ID (int), Department_Name (str)
    Rows: 10 — one row per department.
    """
    path = _resolve_data_path()
    return pd.read_excel(path, sheet_name=SHEET_DEPARTMENT, engine="openpyxl")


@st.cache_data(show_spinner="Loading bed data…")
def load_bed_data() -> pd.DataFrame:
    """
    Load the Bed_Detail sheet.

    Columns: Bed_ID (int), Bed Number (str)
    Rows: 2847 — one row per physical bed record.
    """
    path = _resolve_data_path()
    return pd.read_excel(path, sheet_name=SHEET_BED, engine="openpyxl")


@st.cache_data(show_spinner="Loading all hospital data…")
def load_all_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Convenience loader — returns all four raw DataFrames in one call.

    Returns
    -------
    tuple of (patient_df, staff_df, dept_df, bed_df)
        All DataFrames are raw (unprocessed) as read from the workbook.

    Usage
    -----
    patient_df, staff_df, dept_df, bed_df = load_all_data()
    """
    patient_df = load_patient_data()
    staff_df   = load_staff_data()
    dept_df    = load_department_data()
    bed_df     = load_bed_data()
    return patient_df, staff_df, dept_df, bed_df


def get_sheet_names() -> list[str]:
    """
    Return the sheet names present in the workbook without loading all data.
    Useful for the Dataset Overview panel.
    """
    path = _resolve_data_path()
    if not os.path.exists(path):
        return []
    xl = pd.ExcelFile(path, engine="openpyxl")
    return xl.sheet_names
