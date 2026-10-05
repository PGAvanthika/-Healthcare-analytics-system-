# =============================================================================
# config.py — MediSight Application Configuration
# =============================================================================
# All application-level constants are defined here.
# Do NOT scatter configuration values across multiple files.
# =============================================================================

# ----------------------------------------------------------------------------
# Application Identity
# ----------------------------------------------------------------------------
APPLICATION_NAME = "MediSight"
APPLICATION_SUBTITLE = "Healthcare Analytics & Decision Support System"

# ----------------------------------------------------------------------------
# Data Source
# ----------------------------------------------------------------------------
# Path is relative to the project root (the directory containing app.py).
# Uses the exact filename including the double space in the original file.
DATA_PATH = "data/Hospital  Health Care Management Data set.xlsx"

# ----------------------------------------------------------------------------
# Excel Sheet Names
# ----------------------------------------------------------------------------
SHEET_PATIENT    = "Detail data dataset"
SHEET_STAFF      = "Staff_Detail"
SHEET_DEPARTMENT = "Department"
SHEET_BED        = "Bed_Detail"

# ----------------------------------------------------------------------------
# Column Names — Patient Dataset
# These are the exact column names as they appear in the workbook.
# ----------------------------------------------------------------------------
COL_STAFF_ID      = "Staff_Id"
COL_BED_ID        = "Bed_ID"
COL_DPT_ID        = "Dpt_ID"
COL_PATIENT_ID    = "ID"
COL_NAME          = "Name"
COL_GENDER        = "Gender"
COL_CITY          = "City"
COL_STATE         = "State"
COL_AGE           = "Age"
COL_PATIENT_TYPE  = "Patient type"
COL_STATUS        = "Status"
COL_TREATMENT_COST = "treatemencost"
COL_BED           = "Bed"
COL_LOS           = "LOS"
COL_ER_TIME       = "ER_Time"
COL_DATE          = "Date"
COL_FEEDBACK      = "Feedback"
COL_RATING        = "Rating"
COL_AGE_BUCKET    = "Age Bucket"
COL_CUSTOM        = "Custom"
COL_FZ_ME         = "FZ me"

# ----------------------------------------------------------------------------
# Column Names — Dimension Tables
# ----------------------------------------------------------------------------
COL_DEPT_NAME     = "Department_Name"
COL_STAFF_NAME    = "Staff Name"
COL_BED_NUMBER    = "Bed Number"

# ----------------------------------------------------------------------------
# Known Categorical Values — Status
# Verified from workbook inspection. Used by KPI engine.
# ----------------------------------------------------------------------------
STATUS_NORMAL    = "Normal"
STATUS_DISCHARGE = "Discharge"
STATUS_ICU       = "ICU"
STATUS_DEATH     = "Death"
STATUS_READMIT   = "Readmit"

# ----------------------------------------------------------------------------
# Known Categorical Values — Patient Type
# Note: source data uses lowercase 'outpatient' — preserved as-is.
# ----------------------------------------------------------------------------
PATIENT_TYPE_INPATIENT  = "Inpatient"
PATIENT_TYPE_OUTPATIENT = "outpatient"

# ----------------------------------------------------------------------------
# Operational Thresholds
# ----------------------------------------------------------------------------
# A hospital stay longer than this many days is classified as prolonged.
PROLONGED_STAY_THRESHOLD = 6

# Minimum acceptable age (used for numeric validation)
AGE_MIN = 0
AGE_MAX = 120

# Minimum acceptable treatment cost
TREATMENT_COST_MIN = 0.0

# Minimum/maximum LOS in days
LOS_MIN = 0
LOS_MAX = 365

# Minimum/maximum ER time in minutes
ER_TIME_MIN = 0
ER_TIME_MAX = 1440   # 24 hours in minutes

# Rating scale
RATING_MIN = 1
RATING_MAX = 5

# ----------------------------------------------------------------------------
# UI Layout
# ----------------------------------------------------------------------------
PAGE_TITLE = "MediSight"
PAGE_ICON  = "🏥"
LAYOUT     = "wide"
