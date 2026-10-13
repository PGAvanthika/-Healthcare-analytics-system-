# MediSight — Technical Documentation

**Healthcare Analytics & Decision Support System**
Phases 1, 2, and 3 · Python · Streamlit · Pandas · Plotly

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Data Source and Schema](#4-data-source-and-schema)
5. [Data Processing](#5-data-processing)
6. [Navigation and UI Architecture](#6-navigation-and-ui-architecture)
7. [Global Sidebar Filters](#7-global-sidebar-filters)
8. [KPI Definitions](#8-kpi-definitions)
9. [Phase 1 — Patient Overview Charts](#9-phase-1--patient-overview-charts)
10. [Phase 2 — Diagnostic Analytics](#10-phase-2--diagnostic-analytics)
11. [Phase 3 Feature 1 — Expected LOS Prediction](#11-phase-3-feature-1--expected-los-prediction)
12. [Phase 3 Feature 2 — Bed Demand Forecasting](#12-phase-3-feature-2--bed-demand-forecasting)
13. [Validated Baseline Numbers](#13-validated-baseline-numbers)
14. [Validation and Testing](#14-validation-and-testing)
15. [Limitations and Future Work](#15-limitations-and-future-work)

---

## 1. Project Overview

MediSight is a Streamlit-based healthcare analytics and decision-support application built on a single Excel workbook. All analytics are computed in memory at runtime. The original Excel file is never modified, no data is generated, and no external databases are used.

### Objectives

- Provide hospital managers with dynamic KPI monitoring and exploratory data analytics
- Surface diagnostic patterns: readmissions, ER wait times, length of stay, treatment costs
- Forecast inpatient arrivals and estimate average bed requirements using a statistical baseline
- Serve as an extensible foundation for future predictive features

### Implementation Status

| Phase | Status | Content |
|---|---|---|
| Phase 1 | ✅ Complete | Data loading, preprocessing, 13 KPIs, 5 overview charts, dataset overview, data quality panel |
| Phase 2 | ✅ Complete | Diagnostic Analytics — 4 modules, 17 interactive Plotly charts |
| Phase 3 — Feature 1 | ✅ Complete | Expected LOS Prediction (historical median-based) |
| Phase 3 — Feature 2 | ✅ Complete | Bed Demand Forecasting (SES + Expected LOS) |

---

## 2. Technology Stack

All packages are pinned in `requirements.txt`. Only packages actually used by the application are listed here.

| Library | Version | Role in MediSight |
|---|---|---|
| Python | 3.11 | Runtime |
| `streamlit` | 1.65.0 | Web UI framework, radio navigation, `@st.cache_data` |
| `pandas` | 3.0.6 | All data loading, manipulation, and aggregation |
| `numpy` | 2.4.6 | Numeric operations; SES implementation |
| `plotly` | 7.1.0 | All interactive charts (bar, line, scatter, box, histogram, pie) |
| `openpyxl` | 3.1.5 | Excel engine — `pd.read_excel(..., engine="openpyxl")` |
| `pyarrow` | 25.0.1 | Arrow-backed Pandas internals |
| `altair` | 6.3.0 | Indirect Streamlit dependency (not called directly) |

**No machine-learning libraries are present.** SES is implemented from scratch in NumPy inside `utils/predictive.py`. No model training, no synthetic data generation, no external APIs.

---

## 3. Project Structure

```
medisight/
├── app.py                     # Single entry point (~1,750 lines)
│                              # Page config · CSS · data loading · sidebar
│                              # filter logic · KPI calculation · all render_* functions · router
├── config.py                  # All constants (column names, sheet names, thresholds, UI tokens)
├── requirements.txt           # Pinned dependencies
├── .gitignore
├── TECHNICAL_DOCUMENTATION.md
│
├── data/
│   └── Hospital  Health Care Management Data set.xlsx   ← single source of truth
│
├── utils/
│   ├── __init__.py
│   ├── data_loader.py         # @st.cache_data Excel readers, path resolution
│   ├── preprocessing.py       # 8-step pipeline, QualityReport dataclass
│   ├── metrics.py             # calculate_kpis() → KPIResult dataclass
│   ├── descriptive.py         # 5 Phase 1 overview Plotly charts
│   ├── diagnostic.py          # Phase 2 — threshold helpers + 4 modules + 17 charts
│   └── predictive.py          # Phase 3 — Feature 1 LOS functions + Feature 2 SES engine
│
├── assets/                    # Empty — reserved for future static files
└── pages/                     # Empty — reserved for future multi-page Streamlit expansion
```

### Module Responsibilities

| Module | Key exports / responsibilities |
|---|---|
| `app.py` | `_load_and_preprocess()` · sidebar filters · `filtered_df` · `kpis` · five `render_*` page functions · router `if/elif` block |
| `config.py` | `COL_*` column name constants · `SHEET_*` sheet names · `STATUS_*` / `PATIENT_TYPE_*` category values · operational thresholds · UI layout constants |
| `utils/data_loader.py` | `load_patient_data()` · `load_staff_data()` · `load_department_data()` · `load_bed_data()` · `load_all_data()` · `get_sheet_names()` |
| `utils/preprocessing.py` | `preprocess_patient_data(raw_patient, raw_dept)` → `(processed_df, QualityReport)` · `preprocess_staff_data()` · `preprocess_department_data()` · `preprocess_bed_data()` |
| `utils/metrics.py` | `calculate_kpis(filtered_df, staff_df, bed_df)` → `KPIResult` |
| `utils/descriptive.py` | `plot_patient_type_distribution()` · `plot_status_distribution()` · `plot_department_distribution()` · `plot_monthly_patient_volume()` · `plot_age_distribution()` |
| `utils/diagnostic.py` | `add_derived_diagnostic_cols()` · `compute_*_thresholds()` · Modules A–D: all readmission / ER / LOS / cost functions and charts · `DIAGNOSIS_AVAILABLE` · `DIAGNOSIS_NOTE` |
| `utils/predictive.py` | Feature 1: `overall_los_stats()` · `estimate_los()` · LOS chart functions; Feature 2: `_ses_smooth()` · `_ses_forecast()` · `_find_best_alpha()` · `run_ses_forecast()` · `estimate_bed_demand()` · bed demand chart functions |

---

## 4. Data Source and Schema

**File:** `data/Hospital  Health Care Management Data set.xlsx`
The double space in the filename is intentional and matches the original file exactly.

This file is the **single source of truth**. It is opened read-only with `pd.read_excel(..., engine="openpyxl")`. Its MD5 hash is `9921c00a29b7190f17ab2106830872d5` and is verified unchanged after every run.

### Workbook Sheets

| Sheet Name | Rows | Columns | Purpose |
|---|---|---|---|
| `Detail data dataset` | 2,506 | 21 | Main patient records |
| `Staff_Detail` | 262 | 2 | Staff dimension (`Staff_Id`, `Staff Name`) |
| `Department` | 10 | 2 | Department lookup (`Dpt_ID`, `Department_Name`) |
| `Bed_Detail` | 2,847 | 2 | Bed records (`Bed_ID`, `Bed Number`) |

### Patient Dataset Columns (raw, as in workbook)

| Column | Type | Nulls | Notes |
|---|---|---|---|
| `Staff_Id` | int64 | 0 | FK → Staff_Detail |
| `Bed_ID` | float64 | **755** | Null = no bed assigned (outpatients / non-admitted) |
| `Dpt_ID` | int64 | 0 | FK → Department |
| `ID` | int64 | 0 | Patient ID — 2,506 unique values (max = 4,126; sparse) |
| `Name` | str | 0 | PII — excluded from all display tables |
| `Gender` | str | 0 | `F`, `M` |
| `City` | str | 0 | 16 unique cities |
| `State` | str | 0 | 37 unique states / regions |
| `Age` | int64 | 0 | Range: 1–98 |
| `Patient type` | str | 0 | `Inpatient` or `outpatient` (lowercase 'o') |
| `Status` | str | 0 | `Normal`, `Readmit`, `Discharge`, `ICU`, `Death` |
| `treatemencost` | float64 | 0 | Per-patient treatment cost: $2.54–$1,241.33 |
| `Bed` | str | **755** | Only value present: `Occupied` (null where Bed_ID is null) |
| `LOS` | int64 | 0 | Length of stay in days: 0–32 |
| `ER_Time` | float64 | **719** | ER wait time in minutes: 11–190 (mostly Inpatients missing) |
| `Date` | datetime64 | 0 | Range: 2007-01-01 to 2007-12-31 |
| `Feedback` | str | 0 | 5-point Likert: Fully Agree → Fully Disagree |
| `Rating` | float64 | 0 | 1.0–5.0 |
| `Age Bucket` | str | 0 | `Below 6Y`, `6-20Y`, `21-40Y`, `41-60y`, `60+Y` |
| `Custom` | str | 0 | LOS bucket label (text-based) |
| `FZ me` | str | 0 | Sentiment: `Postive`, `Negative`, `Neutral` |

Only three columns have nulls: `Bed_ID` (755), `Bed` (755), `ER_Time` (719). All other columns are fully populated.

### Status Distribution

| Status | Count | % of Total |
|---|---|---|
| Normal | 1,636 | 65.3% |
| Readmit | 493 | 19.7% |
| Discharge | 209 | 8.3% |
| Death | 86 | 3.4% |
| ICU | 82 | 3.3% |

### Patient Type Split

| Type | Count |
|---|---|
| Inpatient | 1,679 |
| outpatient | 827 |

### Department Summary

| Department | Total | Inpatient | Outpatient |
|---|---|---|---|
| Physical Medicine and Rehabilitation Department | 515 | 515 | 0 |
| OPD Outpatient department (OPD) | 824 | **0** | 824 |
| Surgery | 436 | 436 | 0 |
| OT | 242 | 242 | 0 |
| Dermatology | 169 | 168 | 1 |
| Othopadics | 96 | 96 | 0 |
| Neurology | 72 | 72 | 0 |
| Gynaecology | 59 | 59 | 0 |
| Cardiology | 48 | 47 | 1 |
| oncology | 45 | 44 | 1 |

OPD has zero inpatients and is therefore excluded from inpatient arrival forecasting. Cardiology, Dermatology, and oncology each have exactly one outpatient record (single-record groups are flagged as low-confidence).

### Date Semantics (validated)

Each `(patient_id, date)` pair is unique across all 2,506 records. Multiple patients share the same calendar date (max 77 per day). This is consistent with `Date` representing an admission or encounter date, making it suitable for time-series arrival counting.

### Department Join Safety

The Department sheet has 10 unique `Dpt_ID` values with no nulls. The left-join onto the patient table produces exactly 2,506 rows — no row multiplication, no unmatched patients.

---

## 5. Data Processing

### Data Loading (`utils/data_loader.py`)

Each sheet has a dedicated `@st.cache_data` function. The Excel path resolves relative to the project root — no absolute paths, making the app fully portable. A fallback resolves paths relative to the `utils/` directory if the working directory differs.

| Function | Returns |
|---|---|
| `load_patient_data()` | Raw `Detail data dataset` DataFrame |
| `load_staff_data()` | Raw `Staff_Detail` DataFrame |
| `load_department_data()` | Raw `Department` DataFrame |
| `load_bed_data()` | Raw `Bed_Detail` DataFrame |
| `load_all_data()` | `(patient_df, staff_df, dept_df, bed_df)` tuple |
| `get_sheet_names()` | `list[str]` of sheet names (without loading all data) |

### Preprocessing Pipeline (`utils/preprocessing.py`)

Called once per session inside `_load_and_preprocess()` which is itself `@st.cache_data`. Returns `(processed_df, QualityReport)`.

| Step | Function | Action |
|---|---|---|
| 1 | `_clean_column_names` | Strip leading/trailing whitespace from all column names |
| 2 | `_normalise_empty_strings` | Replace `""` and whitespace-only strings → `NaN` |
| 3 | `_validate_dates` | `pd.to_datetime(errors="coerce")` on `Date`; invalid → `NaT` |
| 4 | `_validate_numerics` | Coerce 5 numeric columns; out-of-range values → `NaN` |
| 5 | `_check_duplicates` | Count fully duplicate rows (retained, not dropped) |
| 6 | `_audit_missing` | Record null counts per column in `QualityReport` |
| 7 | `_enrich_with_department` | Safe left-join on `Dpt_ID` → adds `Department_Name` |
| 8 | `_add_derived_features` | Add 10 runtime-only derived columns |

**Numeric validation ranges:**

| Column | Min | Max | Validation notes |
|---|---|---|---|
| `Age` | 0 | 120 | Out-of-range → NaN |
| `treatemencost` | 0.0 | — | Negative → NaN |
| `LOS` | 0 | 365 | Out-of-range → NaN |
| `ER_Time` | 0 | 1,440 | > 24 hours → NaN |
| `Rating` | 1 | 5 | Out-of-range → NaN |

Current dataset: zero records fail any of these range checks. All values are within valid bounds.

**Derived columns (in-memory only — never written to Excel):**

| Column | Derivation | Source |
|---|---|---|
| `Department_Name` | Left-join on `Dpt_ID` | Department sheet |
| `Year` | `Date.dt.year` | `Date` |
| `Month` | `Date.dt.month` (1–12) | `Date` |
| `Month_Name` | `Date.dt.strftime("%B")` | `Date` |
| `Week` | `Date.dt.isocalendar().week` | `Date` |
| `Quarter` | `Date.dt.quarter` | `Date` |
| `Day` | `Date.dt.day` | `Date` |
| `Day_Name` | `Date.dt.strftime("%A")` | `Date` |
| `Occupied_Bed_Flag` | `1 if Bed_ID is not NaN else 0` | `Bed_ID` |
| `Readmission_Flag` | `1 if Status == "Readmit" else 0` | `Status` |
| `Prolonged_Stay` | `1 if LOS > 6 else 0` | `LOS` (threshold from `config.py`) |

The processed DataFrame has **32 columns** (21 raw + 1 from department join + 10 derived).

### `QualityReport` Dataclass

Every preprocessing run produces a `QualityReport` object surfaced in the Dataset Overview page:

```python
@dataclass
class QualityReport:
    total_rows_raw: int          # = 2,506
    missing_by_column: dict      # {col: null_count} — only Bed_ID, Bed, ER_Time
    duplicate_row_count: int     # = 0
    invalid_dates: int           # = 0
    invalid_numeric: dict        # empty — no out-of-range values in this dataset
    records_nulled: dict         # empty
    notes: list[str]             # human-readable log of all preprocessing actions
```

### Caching Strategy

`_load_and_preprocess()` in `app.py` is `@st.cache_data(show_spinner=False)`. It runs once when Streamlit first loads and caches `(processed_df, staff_df, dept_df, bed_df, quality_report)` for the lifetime of the session. Filter changes never trigger a re-read of the Excel file — they only rebuild `filtered_df` from the cached `processed_df`.

---

## 6. Navigation and UI Architecture

MediSight uses a single `app.py` file with `st.radio` sidebar navigation. All five pages share the same execution context — `filtered_df`, `kpis`, and all cached DataFrames are module-level variables accessible to every `render_*` function as closures.

### Navigation Items

```python
NAV_ITEMS = [
    "📋  Dataset Overview",
    "📊  Hospital KPIs",
    "🩺  Patient Overview",
    "🔬  Diagnostic Analytics",
    "🤖  Predictive Analytics",
]
```

### Router

```python
if   selected_page == NAV_ITEMS[0]: render_dataset_overview()
elif selected_page == NAV_ITEMS[1]: render_hospital_kpis()
elif selected_page == NAV_ITEMS[2]: render_patient_overview()
elif selected_page == NAV_ITEMS[3]: render_diagnostic_analytics()
elif selected_page == NAV_ITEMS[4]: render_predictive_analytics()
```

Only one renderer executes per Streamlit run. All renderers are parameter-less closures over the module scope.

### Design Tokens

| Token | Value | Usage |
|---|---|---|
| `C_BG` | `#F5F8FA` | Page background |
| `C_CARD` | `#FFFFFF` | Metric cards, chart backgrounds |
| `C_PRIMARY` | `#123B5D` | Headers, metric values, primary bars |
| `C_TEAL` | `#0F766E` | ER analysis, teal bars, section headers |
| `C_ACCENT` | `#2A9D8F` | Secondary bars, accent lines |
| `C_TEXT` | `#17324D` | Body text |
| `C_SUBTEXT` | `#64748B` | Labels, captions, axis text |
| `C_BORDER` | `#D9E2EC` | Card borders, dividers |
| `C_AMBER` | `#D97706` | Warnings, moderate-rate indicators |
| `C_RED` | `#B91C1C` | High-severity: death, high readmission rate |
| `C_ACTIVE_BG` | `#E8F4F8` | Nav hover, info banners |

---

## 7. Global Sidebar Filters

All filter widgets live inside `with st.sidebar:` in `app.py`. Variables are module-level and used as closures by all page renderers.

### Active Filters

| Widget | Python variable | Streamlit key | Default | Output type |
|---|---|---|---|---|
| Date From | `date_from` | `"date_from"` | 2007-01-01 | `datetime.date` |
| Date To | `date_to` | `"date_to"` | 2007-12-31 | `datetime.date` |
| Department | `selected_depts` | `"dept_filter"` | `[]` (all depts) | `list[str]` |
| Patient Type | `selected_types` | `"type_filter"` | `[]` (all types) | `list[str]` |
| Gender | `selected_genders` | `"gender_filter"` | `[]` (all) | `list[str]` |
| Age Group | `selected_ages` | `"age_filter"` | `[]` (all) | `list[str]` |
| Status | `selected_statuses` | `"status_filter"` | `[]` (all) | `list[str]` |
| City | `selected_cities` | `"city_filter"` | `[]` (all) | `list[str]` |

Empty list = no restriction applied for that filter (shows all).

All eight widgets are populated dynamically from `processed_df` at startup. Age Group options are shown in logical order: `Below 6Y → 6-20Y → 21-40Y → 41-60y → 60+Y`. All other dropdowns are sorted alphabetically.

### Date Validation

If `date_from > date_to`, a `st.error()` banner is shown and the dates are swapped in-place before filtering. This prevents an empty `filtered_df` from a user mistake while still giving a clear warning.

### Filter Application Logic

```python
filtered_df = processed_df.copy()

# 1. Date range (always applied)
filtered_df = filtered_df[
    (filtered_df["Date"].dt.date >= date_from) &
    (filtered_df["Date"].dt.date <= date_to)
]

# 2. Department (only if at least one selected)
if selected_depts:
    filtered_df = filtered_df[filtered_df["Department_Name"].isin(selected_depts)]

# 3. Patient type (only if at least one selected)
if selected_types:
    filtered_df = filtered_df[filtered_df["Patient type"].isin(selected_types)]

# 4. Gender
if selected_genders:
    filtered_df = filtered_df[filtered_df["Gender"].isin(selected_genders)]

# 5. Age Group
if selected_ages:
    filtered_df = filtered_df[filtered_df["Age Bucket"].isin(selected_ages)]

# 6. Status
if selected_statuses:
    filtered_df = filtered_df[filtered_df["Status"].isin(selected_statuses)]

# 7. City
if selected_cities:
    filtered_df = filtered_df[filtered_df["City"].isin(selected_cities)]
```

### Filter Coverage by Page

| Page | Date | Dept | Type | Gender | Age | Status | City | Note |
|---|---|---|---|---|---|---|---|---|
| Dataset Overview | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Shows full unfiltered dataset structure |
| Hospital KPIs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `calculate_kpis(filtered_df, ...)` |
| Patient Overview | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | All 5 charts use `filtered_df` |
| Diagnostic Analytics | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `add_derived_diagnostic_cols(filtered_df)` |
| Expected LOS (Sec 1–4) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | All LOS functions receive `filtered_df` |
| Bed Demand (Sec 5) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅† | †Further restricted to Inpatient only |

† The Bed Demand section adds `Patient type == "Inpatient"` on top of `filtered_df` inside `build_weekly_inpatient_series()`. The global Patient Type filter is still honoured — if the user has filtered to outpatient only, the inpatient subset will be empty and the forecast will show a "Insufficient data" warning.

### Planned Filters (All Now Active)

All seven filters (Date Range, Department, Patient Type, Gender, Age Group, Status, City) are active. There are no remaining placeholder filters.

---

## 8. KPI Definitions

All 13 KPIs are calculated in `utils/metrics.py` via `calculate_kpis(filtered_df, staff_df, bed_df)` which returns a `KPIResult` dataclass. KPIs are recalculated on every Streamlit rerun after a filter change.

| KPI | Formula (DAX-equivalent) | Source DataFrame |
|---|---|---|
| Total Patients | `DISTINCTCOUNT(ID)` | `filtered_df` |
| Inpatients | `COUNTROWS(Patient type == "Inpatient")` | `filtered_df` |
| Outpatients | `COUNTROWS(Patient type == "outpatient")` | `filtered_df` |
| Total Staff | `DISTINCTCOUNT(Staff_Id)` | `staff_df` ← unfiltered |
| Recorded Occupied Beds | `DISTINCTCOUNT(Bed_ID WHERE Bed_ID IS NOT NULL)` | `filtered_df` |
| Avg LOS | `AVERAGE(LOS)` — NaN excluded | `filtered_df` |
| Avg ER Time | `AVERAGE(ER_Time)` — 719 nulls excluded | `filtered_df` |
| Avg Treatment Cost | `AVERAGE(treatemencost)` | `filtered_df` |
| Total Revenue | `SUM(treatemencost)` | `filtered_df` |
| Deaths | `COUNTROWS(Status == "Death")` | `filtered_df` |
| Discharges | `COUNTROWS(Status == "Discharge")` | `filtered_df` |
| Readmissions | `COUNTROWS(Status == "Readmit")` | `filtered_df` |
| Avg Rating | `AVERAGE(Rating)` — NaN excluded | `filtered_df` |

**Total Staff** always uses the full `staff_df` (262 records from Staff_Detail) regardless of date/department/type filters, because staff members exist independently of patient admission records.

---

## 9. Phase 1 — Patient Overview Charts

**Location:** `utils/descriptive.py` · Rendered in `render_patient_overview()`

Five Plotly charts, all receiving `filtered_df`. No data loading or independent filtering inside any chart function.

| Chart | Type | Source Column | Sort / Order |
|---|---|---|---|
| Patient Type Distribution | Donut (`go.Pie`, hole=0.45) | `Patient type` | By count |
| Patient Status Distribution | Vertical bar | `Status` | Descending by count |
| Patients by Department | Horizontal bar | `Department_Name` | Descending by count |
| Monthly Patient Volume | Line + area fill | `Year`, `Month`, `Month_Name` (derived) | Chronological (Year, Month) |
| Patient Age Distribution | Vertical bar | `Age Bucket` | Logical age order |

**Age order (logical, not alphabetical):** `Below 6Y` → `6-20Y` → `21-40Y` → `41-60y` → `60+Y`

Implemented via `pd.Categorical(..., categories=order, ordered=True)`.

---

## 10. Phase 2 — Diagnostic Analytics

**Location:** `utils/diagnostic.py` · Rendered in `render_diagnostic_analytics()`

All functions accept `filtered_df`. All thresholds adapt to the current filter using Q33/Q66 quantiles — no hardcoded values.

### Derived Diagnostic Columns (`add_derived_diagnostic_cols`)

Three category columns are added to a copy of `filtered_df` at the start of every `render_diagnostic_analytics()` call:

| Column | Categories | Threshold Rule |
|---|---|---|
| `ER_Wait_Category` | Short / Moderate / Long | ≤ Q33, Q33–Q66, > Q66 of `ER_Time` |
| `LOS_Category` | Short Stay / Normal Stay / Prolonged Stay | ≤ Q33, Q33–Q66, > Q66 of `LOS` |
| `Cost_Category` | Low / Medium / High | ≤ Q33, Q33–Q66, > Q66 of `treatemencost` |

Full-dataset thresholds: ER (≤35 / ≤60 min), LOS (≤1 / ≤2 days), Cost (≤$21.92 / ≤$167.73).

### Module A — Readmission Analysis

**Formulas:**

```
Readmission Rate (%) = COUNT(Status == "Readmit") / COUNT(all rows) × 100

Rate(group g) = COUNT(Status = "Readmit" ∩ group = g)
                ────────────────────────────────────── × 100
                COUNT(group = g)
```

Applied to: Department, Patient Type, Age Group, ER_Wait_Category, LOS_Category, Cost_Category.

**Key figures (full dataset):** 493 readmissions / 2,506 = **19.7%** overall.
Physical Medicine & Rehabilitation: 393/515 = **76.3%** — highest by department.

Patterns are labelled "associated factors" — causation is not claimed.

### Module B — ER Wait-Time Analysis

**Coverage:** 1,787 records with valid `ER_Time`; 719 null (mostly Inpatients).

**Full-dataset statistics:** mean = 65.6 min, median = 35.0 min, std = 52.1 min, P75 = 89 min, P90 = 160 min.

Charts: histogram with median reference line, category donut, average ER time by department (horizontal bar), ER time vs LOS scatter coloured by patient type.

### Module C — LOS vs Department

Department is a nominal categorical variable — Pearson correlation between department names and LOS values is not meaningful and is not used. Per-group statistics are computed instead.

A numeric Pearson r between `LOS` and `treatemencost` (both numeric) **is** calculated and shown on the LOS vs Cost scatter chart title.

Charts: average LOS by department (horizontal bar), LOS box plots by department (showing spread, IQR, outliers), LOS vs treatment cost scatter.

### Module D — Treatment Cost Analysis

**No Diagnosis column exists** in any sheet of the workbook. This is stated clearly:
- `DIAGNOSIS_AVAILABLE = False` constant in `diagnostic.py`
- Prominent `st.info()` banner using `DIAGNOSIS_NOTE` in the UI

Analysis groups treatment cost by **Department** — clearly labelled throughout, never mislabelled as "by Diagnosis".

**Full-dataset totals:** Total revenue = $404,488.14. Cardiology has the highest average cost per patient ($266.10); Surgery has the lowest average ($153.36).

---

## 11. Phase 3 Feature 1 — Expected LOS Prediction

**Location:** `utils/predictive.py` · Rendered in `render_predictive_analytics()` sections 1–4

**Method:** Historical median of valid LOS records for the matching patient group. No ML model.

### Why Median

LOS is right-skewed: 755 records have LOS = 0 (same-day/outpatient); max = 32 days. The median is less sensitive to long-stay outliers than the mean and gives a better "typical stay" estimate.

### Grouping Hierarchy

`estimate_los(df, department, patient_type, age_bucket)` tries these levels in order, returning the first with ≥ 1 valid LOS record:

| Level | Filters applied | Example label |
|---|---|---|
| 1 | dept + type + age | "Department + Patient Type + Age Bucket" |
| 2 | dept + type | "Department + Patient Type" |
| 3 | dept only | "Department" |
| 4 | type only | "Patient Type (Inpatient)" |
| 5 | none (fallback) | "Overall (all records)" |

Level 4 was introduced to fix a bug: previously, `estimate_los(df, None, "Inpatient", None)` silently fell through to the overall median (2,506 records) instead of correctly using only inpatient records (1,679). After the fix, the inpatient-only median is used at Level 4 and the bed demand LOS estimate is correct.

### Formulas

```
Expected LOS(group) = MEDIAN(LOS  WHERE  group conditions  AND  LOS IS NOT NULL)
Mean LOS(group)     = AVERAGE(LOS WHERE  group conditions  AND  LOS IS NOT NULL)
```

### Low-Confidence Flag

Groups with fewer than `MIN_GROUP_RECORDS = 5` records are shown with a ⚠ indicator in the results table and an amber-bordered card. The estimate is displayed but caveated.

### UI Sections

| Section | Content |
|---|---|
| 1 — Overall LOS Summary | 4 KPI cards: overall median, valid records, departments, mean LOS |
| 2 — Group Selector | 3 dropdowns (dept, patient type, age bucket) + live estimate card with fallback level shown |
| 3 — Results Table | Dept · Patient Type · Age Bucket · Expected LOS · Mean · Min · Max · Records (⚠ for low-confidence) |
| 4 — Visualisations | Median LOS by dept (H-bar) · Median LOS by dept & type (grouped H-bar) · LOS distribution histogram |

---

## 12. Phase 3 Feature 2 — Bed Demand Forecasting

**Location:** `utils/predictive.py` · Rendered in `render_predictive_analytics()` section 5

**Method:** Simple Exponential Smoothing (SES) on weekly inpatient arrivals, combined with the Expected LOS estimate from Feature 1.

### Stage A — Validate Admission Date

`validate_date_semantics(df)` confirms:
- `Date` column exists and is `datetime64` type ✓
- Zero null dates ✓
- Every `(patient_id, date)` pair is unique across 2,506 records ✓
- Multiple patients share the same calendar date (up to 77/day) ✓

**Conclusion:** `Date` is a valid admission or encounter date and is used as the basis for arrival counting.

### Stage B — Build Weekly Inpatient Series

`build_weekly_inpatient_series(df, department=None)`:

```
1. Filter:  Patient type == "Inpatient"       (1,679 rows in full dataset)
2. Filter:  Department == dept                (optional — if department provided)
3. Group:   (Year, Week) → COUNT(rows)
4. Sort:    chronological order
```

Uses the `Year` and `Week` derived columns from preprocessing. Falls back to computing them from `Date` if absent.

Result for the full 2007 dataset: **52 weekly observations**, total = 1,679, **no zero-weeks** (CV ≈ 1.12).

OPD is excluded automatically (0 inpatient records) and cannot run SES.

### Stage C — Simple Exponential Smoothing

Implemented from scratch in NumPy. No external forecasting library.

**Smoothing equation:**

```
S(0) = Y(0)
S(t) = α × Y(t) + (1 − α) × S(t−1)
```

- `Y(t)` = observed weekly inpatient count for week t  
- `S(t−1)` = previous smoothed level  
- `α` ∈ (0, 1] — higher α gives more weight to recent observations

**All h-step-ahead SES forecasts are constant** (flat) — equal to the last smoothed value `S(n)`. SES does not model trend or seasonality.

### Stage D — Alpha Selection

Grid search over α ∈ {0.05, 0.10, …, 0.95} (step 0.05), minimising MSE on a chronological holdout:

```
holdout_n  = max(4, n // 5)          # ≈ 20% — 10 weeks for the full 52-week series
train      = series[:n − holdout_n]
test       = series[n − holdout_n:]

MSE(α) = mean((test − full(holdout_n, _ses_smooth(train, α)[-1]))²)
best_α = argmin MSE(α)
```

Alpha is selected on `train` only. The `test` period is never seen during selection — no future leakage.

**Optimised alpha on full dataset: α = 0.75** (heavy weight on recent weeks)

### Stage E — Accuracy Metrics

Computed on the holdout period:

```
RMSE = √( mean( (actual − predicted)² ) )
MAE  =    mean( |actual − predicted| )
```

Compared against two baselines on the same holdout:

| Model | Holdout RMSE | Holdout MAE | Note |
|---|---|---|---|
| **SES (α = 0.75)** | **4.99** | **4.15** | Best |
| Naïve (last observed value) | 5.08 | 4.20 | SES marginally better |
| Historical mean (train mean) | 25.32 | 24.87 | SES much better |

The improvement over naïve is modest, which is expected for a high-variance series (CV ≈ 1.1) with no strong trend.

### Stage F — Expected LOS Integration

`estimate_los(df, dept, "Inpatient", None)` is called with `patient_type="Inpatient"` (thanks to the Level 4 fix) so only inpatient LOS records are used. This is consistent with Feature 1 and ensures the bed demand LOS represents inpatient stays only.

### Stage G — Bed Demand Formula

**Convert weekly forecast to daily:**

```
Forecast Daily Arrivals = Forecast Weekly Arrivals ÷ 7
```

**Steady-flow approximation:**

```
Estimated Average Bed Demand ≈ Forecast Daily Arrivals × Expected LOS (days)
```

This is valid when admission and discharge flows are in approximate steady state. It estimates **average concurrent occupancy** — not daily peak, not maximum, not guaranteed capacity.

**Example from validated full dataset (one session run):**
- Forecast weekly ≈ 9.0 inpatients/week
- Forecast daily ≈ 9.0 / 7 ≈ 1.29/day
- Expected LOS (Inpatient, all departments) = 2.0 days
- Estimated avg bed demand ≈ 1.29 × 2.0 ≈ **2.57 beds**

Note: the SES forecast value is session-specific and changes with different filter selections.

### UI Sections (within `render_predictive_analytics()` section 5)

| Section | Content |
|---|---|
| Date semantics validation | Collapsible expander confirming Date is a valid admission date |
| Forecast controls | Horizon selector (2/4/8/12 weeks), department selector, historical period note |
| Forecast summary KPIs | 4 cards: Forecast/week, Forecast/day, Expected LOS, Avg Bed Demand |
| Formula display | Dynamic: `X arrivals/day × Y days LOS = Z beds` |
| Model parameters | α, RMSE, MAE, holdout period, + baseline comparison (naïve vs mean) |
| Historical arrivals & forecast chart | Observed (primary line) + SES fit (dashed) + forecast (amber + band) |
| Holdout validation chart | Actual vs SES predicted for the last ~10 weeks |
| Department bed demand comparison | Bar chart + table: per-dept forecast, LOS, avg beds |
| Methodology & limitations expander | SES equation, RMSE/MAE formulas, data notes, limitations |

### Functions in `utils/predictive.py`

| Function | Description |
|---|---|
| `validate_date_semantics(df)` | Returns `{valid: bool, notes: list[str]}` |
| `build_weekly_inpatient_series(df, dept)` | Inpatient-only weekly count series |
| `_ses_smooth(series, alpha)` | Pure NumPy SES: `S(t) = α·Y(t) + (1−α)·S(t−1)` |
| `_ses_forecast(series, alpha, horizon)` | Returns flat array of length `horizon` |
| `_find_best_alpha(series)` | Grid search → `(best_alpha, holdout_mse, holdout_rmse)` |
| `run_ses_forecast(df, dept, horizon_weeks)` | Full pipeline → dict with RMSE, MAE, baselines |
| `estimate_bed_demand(forecast_daily, expected_los)` | `avg_beds = daily × LOS` |
| `department_bed_demand_table(df, horizon_weeks)` | Per-dept comparison DataFrame |
| `plot_ses_forecast(ses_result, horizon, label)` | Historical + SES fit + forecast line chart |
| `plot_holdout_validation(ses_result)` | Actual vs predicted on holdout period |
| `plot_bed_demand_bar(dept_table)` | H-bar: avg bed demand by department |

---

## 13. Validated Baseline Numbers

All values verified against the real Excel workbook (MD5: `9921c00a29b7190f17ab2106830872d5`).

### 13 KPIs — Full Unfiltered Dataset

| KPI | Value |
|---|---|
| Total Patients | 2,506 |
| Inpatients | 1,679 |
| Outpatients | 827 |
| Total Staff | 262 |
| Recorded Occupied Beds | 1,751 |
| Avg LOS | 1.70 days |
| Avg ER Time | 65.63 min |
| Avg Treatment Cost | $161.41 |
| Total Treatment Revenue | $404,488.14 |
| Deaths | 86 |
| Discharges | 209 |
| Readmissions | 493 |
| Avg Patient Rating | 4.75 / 5.0 |

### Feature 1 — LOS Estimates

| Group | Median LOS | Records | Level |
|---|---|---|---|
| Overall (all) | 2.0 days | 2,506 | Level 5 |
| Inpatient only | 2.0 days | 1,679 | Level 4 |
| outpatient only | 0.0 days | 827 | Level 4 |
| Surgery / Inpatient | 2.0 days | 436 | Level 2 |
| OPD / outpatient | 0.0 days | 824 | Level 2 |
| PMR / Inpatient | 2.0 days | 515 | Level 2 |
| Gynaecology / Inpatient | 2.0 days | 59 | Level 2 |

### Feature 2 — SES Forecast (full 52-week series)

| Metric | Value |
|---|---|
| Optimised α | 0.75 |
| Holdout period | Last 10 weeks |
| Holdout RMSE | 4.99 inpatients/week |
| Holdout MAE | 4.15 inpatients/week |
| Naïve baseline RMSE | 5.08 |
| Historical mean RMSE | 25.32 |
| SES vs naïve | SES better (RMSE 4.99 < 5.08) |
| SES vs mean | SES much better |

### Diagnostic Analytics

| Metric | Value |
|---|---|
| Overall readmission rate | 19.7% |
| PMR dept readmission rate | 76.3% |
| Full-dataset total revenue | $404,488.14 |
| ER time mean | 65.6 min |
| ER time median | 35.0 min |
| Q1 2007 (Jan–Mar) patient records | 1,175 |

---

## 14. Validation and Testing

All tests run against the real Excel workbook. No mocking, no synthetic data.

### Compilation
- `app.py` — compiles without syntax errors ✅
- `utils/predictive.py` — compiles without syntax errors ✅

### KPI Regression (7 values, run on every validation cycle)

| Check | Expected | Status |
|---|---|---|
| Total Patients | 2,506 | ✅ |
| Inpatients | 1,679 | ✅ |
| Outpatients | 827 | ✅ |
| Total Staff | 262 | ✅ |
| Deaths | 86 | ✅ |
| Discharges | 209 | ✅ |
| Readmissions | 493 | ✅ |

### Feature 1 — Patient-Type Filter Fix

| Check | Before Fix | After Fix |
|---|---|---|
| `estimate_los(df, None, "Inpatient", None)` records | 2,506 (bug) | 1,679 ✅ |
| `estimate_los(df, None, "outpatient", None)` records | 2,506 (bug) | 827 ✅ |
| `estimate_los(df, "Surgery", "Inpatient", None)` records | 436 | 436 ✅ |
| `estimate_los(df, None, None, None)` records | 2,506 | 2,506 ✅ |

### Feature 2 — SES Math

| Check | Result |
|---|---|
| `_ses_smooth(series, α=1.0)` reproduces input series | ✅ |
| S(0), S(1), S(2) manually verified | ✅ |
| `_ses_forecast` returns constant flat array | ✅ |
| Alpha grid-search produces valid α ∈ (0.05, 0.95) | ✅ |
| Total inpatients across all 52 weekly obs = 1,679 | ✅ |
| Surgery weekly total = 436 | ✅ |
| Zero zero-count weeks in full series | ✅ |
| RMSE and MAE recalculated from first principles — match stored values | ✅ |
| Alpha chosen on train-only (no leakage) — holdout RMSE matches independent recalculation | ✅ |

### Filters

| Check | Result |
|---|---|
| `date_from > date_to` → error banner + swap | ✅ |
| Q1 2007 (Jan–Mar) filter → 1,175 records | ✅ |
| Cardiology filter → 48 records | ✅ |
| Patient type "Inpatient" → 1,679 | ✅ |
| Patient type "outpatient" → 827 | ✅ |
| SES on Q1 filter → 13 weekly obs, 730 total inpatients | ✅ |

### Empty / Insufficient Data Safety

| Check | Result |
|---|---|
| `overall_los_stats(empty_df)` returns `{}` | ✅ |
| `estimate_los(empty_df, ...)` returns `no_data=True` | ✅ |
| `run_ses_forecast(empty_df)` returns `success=False` | ✅ |
| All chart functions handle empty DataFrame without exception | ✅ |

### Excel Integrity

| Check | Result |
|---|---|
| MD5 `9921c00a29b7190f17ab2106830872d5` unchanged | ✅ |
| No CSV / Excel / DB write operations anywhere in codebase | ✅ |

### Streamlit Smoke Test

| Check | Result |
|---|---|
| `streamlit run app.py` starts without errors | ✅ |
| HTTP 200 on `localhost:8502` | ✅ |
| No Python exceptions in server log | ✅ |

---

## 15. Limitations and Future Work

### Current Limitations

| Area | Limitation |
|---|---|
| Data coverage | Single year (2007) — year-over-year trends and seasonal cross-validation are not possible |
| ER_Time | 28.7% missing (719/2,506) — mostly Inpatients; ER analysis covers a subset of records |
| Bed occupancy metric | "Recorded Occupied Beds" = unique Bed_IDs in patient records, not live occupancy |
| Diagnosis | No Diagnosis column in any sheet — cost analysis by diagnosis is not feasible |
| SES forecast shape | Flat/constant forecast — no trend or seasonality modelling |
| SES vs naïve | Improvement is modest (RMSE 4.99 vs 5.08) for this high-variance, single-year series |
| Bed capacity | No operational bed capacity data → occupancy percentage cannot be calculated |
| LOS = 0 | 755 same-day records (LOS = 0) are included in all LOS statistics; may dilute inpatient averages |
| outpatient (lowercase) | Source data uses lowercase 'o' — must be matched exactly in all string comparisons |

### Completed Phases

| Phase | Deliverable |
|---|---|
| Phase 1 | Data pipeline, 13 KPIs, 5 overview charts, data quality panel, healthcare theme |
| Phase 2 | Diagnostic Analytics — 4 modules, 17 charts, adaptive thresholds |
| Phase 3 F1 | Expected LOS Prediction — median, group hierarchy (5 levels), low-confidence flags |
| Phase 3 F2 | Bed Demand Forecasting — SES, α optimisation, MAE/RMSE, baselines, dept table |

### Planned Future Enhancements

- Gender, Age Group, Status, City sidebar filters (placeholders exist)
- Trend forecasting (Holt's double smoothing) if multi-year data becomes available
- Readmission risk scoring (logistic regression or gradient boosting)
- Treatment cost estimation by patient profile
- Multi-year data integration for seasonal decomposition and better forecast accuracy

---

*MediSight — Phases 1, 2, and 3 fully implemented and validated.*
*All figures are sourced from the real Excel workbook. No synthetic data, no hardcoded values.*
