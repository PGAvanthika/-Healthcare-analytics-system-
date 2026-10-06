# MediSight — Complete Technical Documentation

**Healthcare Analytics & Decision Support System**  
Phases 1 and 2 — Built on Python · Streamlit · Pandas · Plotly

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Data Source](#3-data-source)
4. [Project Structure](#4-project-structure)
5. [Data Inspection Results](#5-data-inspection-results)
6. [Configuration — config.py](#6-configuration--configpy)
7. [Data Loading — utils/data_loader.py](#7-data-loading--utilsdata_loaderpy)
8. [Preprocessing Pipeline — utils/preprocessing.py](#8-preprocessing-pipeline--utilspreprocessingpy)
9. [KPI Engine — utils/metrics.py](#9-kpi-engine--utilsmetricspy)
10. [Phase 1 Charts — utils/descriptive.py](#10-phase-1-charts--utilsdescriptivepy)
11. [Phase 2 Diagnostics — utils/diagnostic.py](#11-phase-2-diagnostics--utilsdiagnosticpy)
12. [Application Entry Point — app.py](#12-application-entry-point--apppy)
13. [All Formulas and Rules](#13-all-formulas-and-rules)
14. [Data Rules and Constraints](#14-data-rules-and-constraints)
15. [Validation Results](#15-validation-results)
16. [Known Limitations](#16-known-limitations)

---

## 1. Project Overview

MediSight is a Streamlit-based healthcare analytics dashboard that reads a single Excel workbook and computes all analytics in memory. No data is generated, no files are written, and the original Excel file is never modified.

| Phase | Status | Content |
|---|---|---|
| Phase 1 | ✅ Complete | Data loading, preprocessing, 13 KPIs, 5 overview charts, data quality panel |
| Phase 2 | ✅ Complete | Diagnostic Analytics — 4 analysis modules, 17 Plotly charts |
| Phase 3 | 🔲 Planned | Predictive Analytics |

---

## 2. Technology Stack

| Library | Version | Purpose |
|---|---|---|
| Python | 3.x | Runtime |
| Streamlit | 1.65.0 | Web UI framework |
| Pandas | 3.0.6 | Data manipulation and aggregations |
| NumPy | 2.4.6 | Numeric operations |
| Plotly | 7.1.0 | Interactive charts |
| OpenPyXL | 3.1.5 | Excel file reading |

No machine-learning libraries. No model training. No synthetic data generation.

---

## 3. Data Source

**File:** `data/Hospital  Health Care Management Data set.xlsx`  
(Double space in filename is intentional — matches the original file exactly.)

This file is the **single source of truth**. All calculations happen in Python memory at runtime. The file is opened read-only via `pd.read_excel(..., engine="openpyxl")`.

### Workbook Sheets

| Sheet Name | Rows | Columns | Purpose |
|---|---|---|---|
| `Detail data dataset` | 2,506 | 21 | Main patient records |
| `Staff_Detail` | 262 | 2 | Staff dimension table |
| `Department` | 10 | 2 | Department lookup table |
| `Bed_Detail` | 2,847 | 2 | Bed dimension table |

---

## 4. Project Structure

```
medisight/
├── app.py                   # Streamlit entry point — UI and routing
├── config.py                # All constants, column names, thresholds
├── requirements.txt         # Pinned dependencies
├── .gitignore
│
├── data/
│   └── Hospital  Health Care Management Data set.xlsx
│
├── utils/
│   ├── __init__.py
│   ├── data_loader.py       # Excel reading with @st.cache_data
│   ├── preprocessing.py     # Cleaning, validation, enrichment, derived features
│   ├── metrics.py           # 13-KPI engine
│   ├── descriptive.py       # Phase 1 — 5 overview charts
│   └── diagnostic.py        # Phase 2 — 17 diagnostic charts + stats functions
│
├── assets/                  # Static assets (reserved for future phases)
└── pages/                   # Reserved for future multi-page expansion
```

---

## 5. Data Inspection Results

### Patient Dataset Columns

| Column | Type | Nulls | Notes |
|---|---|---|---|
| `Staff_Id` | int64 | 0 | Foreign key to Staff_Detail |
| `Bed_ID` | float64 | **755** | Null = no bed assigned (outpatients) |
| `Dpt_ID` | int64 | 0 | Foreign key to Department |
| `ID` | int64 | 0 | Patient ID — 2,506 unique values (sparse, max=4,126) |
| `Name` | str | 0 | PII — excluded from all display tables |
| `Gender` | str | 0 | Values: `F`, `M` |
| `City` | str | 0 | 16 unique cities |
| `State` | str | 0 | 37 unique states/regions |
| `Age` | int64 | 0 | Range: 1–98 |
| `Patient type` | str | 0 | Values: `Inpatient`, `outpatient` |
| `Status` | str | 0 | 5 values — see below |
| `treatemencost` | float64 | 0 | Range: $2.54–$1,241.33 |
| `Bed` | str | 755 | Only value present: `Occupied` |
| `LOS` | int64 | 0 | Range: 0–32 days |
| `ER_Time` | float64 | **719** | Range: 11–190 minutes (mostly Inpatients missing) |
| `Date` | datetime64 | 0 | Range: 2007-01-01 to 2007-12-31 |
| `Feedback` | str | 0 | 5 Likert values |
| `Rating` | float64 | 0 | Range: 1.0–5.0 |
| `Age Bucket` | str | 0 | 5 age groups |
| `Custom` | str | 0 | LOS bucket labels (text) |
| `FZ me` | str | 0 | Sentiment: Positive / Negative / Neutral |

### Status Value Counts (full dataset)

| Status | Count | % |
|---|---|---|
| Normal | 1,636 | 65.3% |
| Readmit | 493 | 19.7% |
| Discharge | 209 | 8.3% |
| Death | 86 | 3.4% |
| ICU | 82 | 3.3% |

### Patient Type Counts

| Type | Count |
|---|---|
| Inpatient | 1,679 |
| outpatient | 827 |

### Key Relationship Findings

- `Department` join on `Dpt_ID` is **safe** — 10 unique Dpt_IDs in both tables, merge produces exactly 2,506 rows (no multiplication).
- `Staff_Detail` has 262 rows, one per unique staff member.
- `Bed_Detail` has 2,847 rows but 755 patients have no `Bed_ID` — typically outpatients.
- **No Diagnosis column** exists in any sheet — cost analysis by diagnosis is not possible.
- Date range covers exactly **one calendar year**: 2007.

---

## 6. Configuration — config.py

All application constants live in a single file. Nothing is hardcoded across multiple modules.

### Key Constants

```python
APPLICATION_NAME     = "MediSight"
APPLICATION_SUBTITLE = "Healthcare Analytics & Decision Support System"
DATA_PATH            = "data/Hospital  Health Care Management Data set.xlsx"

# Sheet names
SHEET_PATIENT    = "Detail data dataset"
SHEET_STAFF      = "Staff_Detail"
SHEET_DEPARTMENT = "Department"
SHEET_BED        = "Bed_Detail"

# Operational thresholds
PROLONGED_STAY_THRESHOLD = 6   # days — LOS > 6 = Prolonged_Stay flag

# Validation ranges
AGE_MIN = 0,  AGE_MAX = 120
LOS_MIN = 0,  LOS_MAX = 365
ER_TIME_MIN = 0,  ER_TIME_MAX = 1440  # 24 hours in minutes
RATING_MIN = 1,   RATING_MAX = 5
TREATMENT_COST_MIN = 0.0
```

### Status and Patient Type Constants

```python
STATUS_NORMAL    = "Normal"
STATUS_DISCHARGE = "Discharge"
STATUS_ICU       = "ICU"
STATUS_DEATH     = "Death"
STATUS_READMIT   = "Readmit"

PATIENT_TYPE_INPATIENT  = "Inpatient"
PATIENT_TYPE_OUTPATIENT = "outpatient"   # lowercase — preserved from source
```

---

## 7. Data Loading — utils/data_loader.py

### Design Principle

- Uses `@st.cache_data` on every function so the Excel file is only read once per session, regardless of how many UI interactions occur.
- All paths are resolved relative to the project root using `os.path.abspath(__file__)` as a fallback — the app is fully portable (no hardcoded absolute paths).

### Functions

| Function | Returns | Description |
|---|---|---|
| `load_workbook()` | `dict[str, DataFrame]` | All sheets keyed by name |
| `load_patient_data()` | `DataFrame` | `Detail data dataset` sheet |
| `load_staff_data()` | `DataFrame` | `Staff_Detail` sheet |
| `load_department_data()` | `DataFrame` | `Department` sheet |
| `load_bed_data()` | `DataFrame` | `Bed_Detail` sheet |
| `load_all_data()` | `tuple[df, df, df, df]` | All four in one call |
| `get_sheet_names()` | `list[str]` | Sheet names without loading all data |

### Path Resolution Logic

```python
def _resolve_data_path() -> str:
    if os.path.exists(DATA_PATH):         # Works when cwd == project root
        return DATA_PATH
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)  # utils/ → medisight/
    candidate = os.path.join(project_root, DATA_PATH)
    if os.path.exists(candidate):
        return candidate
    return DATA_PATH                      # Caller handles FileNotFoundError
```

---

## 8. Preprocessing Pipeline — utils/preprocessing.py

The pipeline runs **once per session** (results are cached). It never writes to the Excel file. Invalid values become `NaN` — records are never silently dropped.

### Pipeline Stages (in order)

| Step | Function | Action |
|---|---|---|
| 1 | `_clean_column_names` | Strip whitespace from all column names |
| 2 | `_normalise_empty_strings` | Replace `""` / whitespace-only strings with `NaN` |
| 3 | `_validate_dates` | Parse `Date` column with `errors="coerce"` → invalid dates become `NaT` |
| 4 | `_validate_numerics` | Coerce 5 numeric columns; out-of-range values → `NaN` |
| 5 | `_check_duplicates` | Count fully duplicate rows (retained, not dropped) |
| 6 | `_audit_missing` | Count nulls per column for the QualityReport |
| 7 | `_enrich_with_department` | Safe left-join to add `Department_Name` |
| 8 | `_add_derived_features` | Add 10 runtime-derived columns |

### Numeric Validation Rules

| Column | Min | Max | Rule |
|---|---|---|---|
| `Age` | 0 | 120 | Out-of-range → NaN |
| `treatemencost` | 0.0 | None | Negative values → NaN |
| `LOS` | 0 | 365 | Out-of-range → NaN |
| `ER_Time` | 0 | 1440 | Out-of-range → NaN |
| `Rating` | 1 | 5 | Out-of-range → NaN |

### Department Enrichment — Safety Checks

Before merging `Department_Name` into the patient table:

1. `Dpt_ID` must exist in both DataFrames
2. `Dpt_ID` in Department table must be **unique** (prevents row multiplication)
3. `Dpt_ID` in Department table must have **no nulls**
4. Row count must not change after merge (`len(merged) == len(patient_df)`)

All four checks pass on this dataset → merge proceeds safely.

### Derived Features

These columns exist only in memory and are never written to Excel.

**Date-based** (from `Date` column):

| Column | Derivation |
|---|---|
| `Year` | `Date.dt.year` |
| `Month` | `Date.dt.month` (1–12) |
| `Month_Name` | `Date.dt.strftime("%B")` (e.g. "January") |
| `Week` | `Date.dt.isocalendar().week` |
| `Quarter` | `Date.dt.quarter` |
| `Day` | `Date.dt.day` |
| `Day_Name` | `Date.dt.strftime("%A")` (e.g. "Monday") |

**Operational** (from existing columns):

| Column | Formula | Source |
|---|---|---|
| `Occupied_Bed_Flag` | `1 if Bed_ID is not NaN, else 0` | `Bed_ID` |
| `Readmission_Flag` | `1 if Status == "Readmit", else 0` | `Status` |
| `Prolonged_Stay` | `1 if LOS > 6, else 0` | `LOS`, threshold from `config.py` |

### QualityReport Dataclass

Every preprocessing run produces a `QualityReport` object with:

```python
@dataclass
class QualityReport:
    total_rows_raw: int          # rows before any processing
    missing_by_column: dict      # {column_name: null_count}
    duplicate_row_count: int     # fully duplicate rows (retained)
    invalid_dates: int           # dates coerced to NaT
    invalid_numeric: dict        # {column_name: count_coerced}
    records_nulled: dict         # {column_name: total_nulled}
    notes: list[str]             # human-readable log of all actions
```

---

## 9. KPI Engine — utils/metrics.py

### Architecture

The function `calculate_kpis(df, staff_df, bed_df)` accepts a **filtered** patient DataFrame. KPIs recompute automatically when filters change — no hardcoded values anywhere.

```
filtered_df  →  calculate_kpis()  →  KPIResult (13 fields)
```

Staff count always uses the full `staff_df` (not the filtered patient DataFrame) because staff exist independently of the patient filter window.

### KPI Formulas

| KPI | Formula | Notes |
|---|---|---|
| **Total Patients** | `nunique(ID)` | Unique patient IDs |
| **Inpatients** | `COUNT(rows where Patient type == "Inpatient")` | |
| **Outpatients** | `COUNT(rows where Patient type == "outpatient")` | Lowercase preserved from source |
| **Total Staff** | `nunique(Staff_Id)` on Staff_Detail table | Not filtered with patient filters |
| **Recorded Occupied Beds** | `nunique(Bed_ID)` where Bed_ID is not null | Unique beds referenced in patient records |
| **Avg LOS** | `mean(LOS)` | NaN values excluded automatically |
| **Avg ER Time** | `mean(ER_Time)` | 719 null values excluded automatically |
| **Avg Treatment Cost** | `mean(treatemencost)` | Per-patient monetary amount |
| **Total Revenue** | `sum(treatemencost)` | Sum of all per-patient costs |
| **Deaths** | `COUNT(rows where Status == "Death")` | |
| **Discharges** | `COUNT(rows where Status == "Discharge")` | |
| **Readmissions** | `COUNT(rows where Status == "Readmit")` | |
| **Avg Rating** | `mean(Rating)` | Scale 1–5 |

### Validated Baseline Values (full unfiltered dataset)

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
| Total Revenue | $404,488.14 |
| Deaths | 86 |
| Discharges | 209 |
| Readmissions | 493 |
| Avg Rating | 4.75 / 5.0 |

---

## 10. Phase 1 Charts — utils/descriptive.py

All 5 functions accept the **already-filtered** patient DataFrame and return a Plotly `Figure`. No data loading or re-filtering inside these functions.

### Chart 1 — Patient Type Distribution (Donut)

- **Source column:** `Patient type`
- **Type:** `go.Pie` with `hole=0.45`
- **Shows:** Count and percentage per category
- **Categories:** `Inpatient`, `outpatient`

### Chart 2 — Patient Status Distribution (Vertical Bar)

- **Source column:** `Status`
- **Type:** `go.Bar`
- **Sorted:** Descending by count
- **Colour coding:** Per-status semantic colours (Normal=teal, Readmit=amber, Discharge=accent, ICU=orange, Death=red)

### Chart 3 — Patients by Department (Horizontal Bar)

- **Source column:** `Department_Name` (added by preprocessing — no additional merge)
- **Type:** `go.Bar` with `orientation="h"`
- **Sorted:** Descending by count
- **Dynamic height:** `max(300, n_departments × 42 + 80)` pixels

### Chart 4 — Monthly Patient Volume (Line)

- **Source columns:** `Year`, `Month`, `Month_Name` (derived during preprocessing)
- **Type:** `go.Scatter` with `mode="lines+markers"` and `fill="tozeroy"`
- **Grouping:** `groupby(["Year","Month","Month_Name"]).size()`
- **Sort:** `sort_values(["Year","Month"])` — chronological order, never alphabetical
- **Label format:** `"Jan 2007"`, `"Feb 2007"` etc.

### Chart 5 — Age Distribution (Vertical Bar)

- **Source column:** `Age Bucket`
- **Type:** `go.Bar`
- **Order:** `["Below 6Y", "6-20Y", "21-40Y", "41-60y", "60+Y"]` (logical, not alphabetical)
- Implemented via `pd.Categorical(..., categories=order, ordered=True)`

---

## 11. Phase 2 Diagnostics — utils/diagnostic.py

### Design Principles

1. Every threshold is computed from the actual data using **quantiles** — never arbitrary magic numbers
2. Categorical variables (e.g. Department) are never Pearson-correlated with numeric values — group statistics are used instead
3. Readmission patterns are labelled as **"associated factors"** — causation is never claimed
4. The absence of a Diagnosis column is clearly declared with `DIAGNOSIS_AVAILABLE = False`

### Derived Diagnostic Columns

Added by `add_derived_diagnostic_cols(df)` — thresholds computed fresh for each filtered slice.

#### ER_Wait_Category

```
Q33_ER = PERCENTILE(ER_Time, 0.33)   [= 35 min on full dataset]
Q66_ER = PERCENTILE(ER_Time, 0.66)   [= 60 min on full dataset]

ER_Wait_Category =
    "Short"    if ER_Time ≤ Q33_ER
    "Moderate" if Q33_ER < ER_Time ≤ Q66_ER
    "Long"     if ER_Time > Q66_ER
    NaN        if ER_Time is NaN
```

#### LOS_Category

```
Q33_LOS = PERCENTILE(LOS, 0.33)   [= 1 day on full dataset]
Q66_LOS = PERCENTILE(LOS, 0.66)   [= 2 days on full dataset]

LOS_Category =
    "Short Stay"     if LOS ≤ Q33_LOS
    "Normal Stay"    if Q33_LOS < LOS ≤ Q66_LOS
    "Prolonged Stay" if LOS > Q66_LOS
    NaN              if LOS is NaN
```

#### Cost_Category

```
Q33_Cost = PERCENTILE(treatemencost, 0.33)   [= $21.92 on full dataset]
Q66_Cost = PERCENTILE(treatemencost, 0.66)   [= $167.73 on full dataset]

Cost_Category =
    "Low"    if treatemencost ≤ Q33_Cost
    "Medium" if Q33_Cost < treatemencost ≤ Q66_Cost
    "High"   if treatemencost > Q66_Cost
    NaN      if treatemencost is NaN
```

> **Why Q33/Q66?** Equal-population tertile bins. Adapts to every filtered slice — "High" always means upper third of costs in the current view.

---

### Module A — Readmission Analysis

#### Core Formula

```
Readmission Rate (%) = (COUNT(Status == "Readmit") / COUNT(all rows)) × 100

Rate by Group:
Rate(g) = COUNT(Status == "Readmit" WHERE Group == g)
          ────────────────────────────────────────────  × 100
          COUNT(all rows WHERE Group == g)
```

Applied to: Department, Patient Type, Age Bucket, ER_Wait_Category, LOS_Category, Cost_Category.

#### Charts (6)

| Chart | Type | Key |
|---|---|---|
| Readmission Rate by Department | H-bar | Rate ≥20% → red, ≥10% → amber, <10% → teal |
| Readmission by Patient Type | Grouped bar | Readmitted vs Not Readmitted |
| Readmission Rate by Age Group | V-bar | Logical age order |
| Rate by ER Wait Category | V-bar | Short / Moderate / Long |
| Rate by LOS Category | V-bar | Short Stay / Normal Stay / Prolonged Stay |
| Rate by Cost Category | V-bar | Low / Medium / High |

Plus: **Readmission Breakdown Table** — all 6 factors combined, 26 rows.

---

### Module B — ER Wait-Time Analysis

#### Summary Statistics

```
count   = COUNT(ER_Time WHERE not NaN)   = 1,787
missing = COUNT(ER_Time WHERE NaN)       = 719
mean    = AVERAGE(ER_Time)               = 65.6 min
median  = MEDIAN(ER_Time)                = 35.0 min
std     = STDEV(ER_Time)                 = 52.1 min
p25     = PERCENTILE(ER_Time, 0.25)      = 35.0 min
p75     = PERCENTILE(ER_Time, 0.75)      = 89.0 min
p90     = PERCENTILE(ER_Time, 0.90)      = 160.0 min
```

#### Charts (4)

| Chart | Type | Note |
|---|---|---|
| ER Wait-Time Distribution | Histogram 30 bins | Median reference vline |
| Avg ER Time by Department | H-bar | Patients with ER data only |
| ER Wait Category Donut | Pie hole=0.42 | Three-slice |
| ER Time vs LOS Scatter | Scatter | Coloured by Patient Type |

---

### Module C — LOS vs Department Analysis

#### Why No Pearson r with Department

Department is nominal categorical — correlating it with LOS using Pearson r is meaningless. Group statistics are used:

```
For each department D:
    Mean_LOS(D)   = AVERAGEIF(Department_Name = D, LOS)
    Median_LOS(D) = MEDIANIF(Department_Name = D, LOS)
    Std_LOS(D)    = STDEVIF(Department_Name = D, LOS)
```

#### Pearson r — LOS vs Cost (numeric ↔ numeric — appropriate)

```
r = CORR(LOS, treatemencost)
  = cov(LOS, treatemencost) / (std(LOS) × std(treatemencost))
```

Displayed on the scatter chart title.

#### Charts (3)

| Chart | Type | Note |
|---|---|---|
| Avg LOS by Department | H-bar | Mean LOS per department |
| LOS Distribution by Department | Box plot | `boxmean="sd"` — shows std dev ring |
| LOS vs Treatment Cost | Scatter | Pearson r in title, coloured by Patient Type |

---

### Module D — Treatment Cost Analysis

#### Diagnosis Availability

```python
DIAGNOSIS_AVAILABLE = False
```

No Diagnosis column exists in any sheet. A prominent `st.info()` banner states this clearly. Department is used as the clinical grouping variable and is labelled accordingly throughout.

#### Cost Statistics

```
For each department D:
    Total_Revenue(D) = SUMIF(Department_Name = D, treatemencost)
    Mean_Cost(D)     = AVERAGEIF(Department_Name = D, treatemencost)
    Median_Cost(D)   = MEDIANIF(Department_Name = D, treatemencost)
    Q25(D)           = PERCENTILE(treatemencost | Dept=D, 0.25)
    Q75(D)           = PERCENTILE(treatemencost | Dept=D, 0.75)
```

#### Charts (4)

| Chart | Type | Note |
|---|---|---|
| Treatment Cost Distribution | Histogram 40 bins | Median reference vline |
| Cost by Department | Box plot | `boxmean="sd"` |
| Avg Treatment Cost by Dept | H-bar | Mean cost |
| Total Revenue by Dept | H-bar | Sum of costs |

---

## 12. Application Entry Point — app.py

### Navigation Architecture

Single-file Streamlit app with `st.radio` navigation. One execution pass serves all pages — `filtered_df` and `kpis` are computed once and shared.

```
Sidebar filters
    ↓
filtered_df = apply(processed_df, date_range, department, patient_type)
    ↓
kpis = calculate_kpis(filtered_df, staff_df, bed_df)
    ↓
render_*(filtered_df, kpis)   ← selected page only
```

### Global Filters

| Filter | Column | Logic |
|---|---|---|
| Date Range (From/To) | `Date` | `date_from ≤ Date.dt.date ≤ date_to` |
| Department | `Department_Name` | `IN selected_depts` (if any selected) |
| Patient Type | `Patient type` | `IN selected_types` (if any selected) |

All Phase 1 and Phase 2 analyses use the same `filtered_df`.

### Healthcare Colour Palette

| Token | Hex | Usage |
|---|---|---|
| Background | `#F5F8FA` | Page background |
| Card | `#FFFFFF` | Metric cards, chart backgrounds |
| Primary | `#123B5D` | Headers, metric values |
| Teal | `#0F766E` | ER analysis, positive indicators |
| Accent | `#2A9D8F` | Secondary bars |
| Text | `#17324D` | Body text |
| Subtext | `#64748B` | Labels, axis text |
| Border | `#D9E2EC` | Card borders |
| Amber | `#D97706` | Warning rates (10–20%) |
| Red | `#B91C1C` | High severity (rates >20%, deaths) |

---

## 13. All Formulas and Rules

### KPI Formulas (DAX Equivalents)

```
Total Patients         = DISTINCTCOUNT(ID)
Inpatients             = COUNTROWS(FILTER(df, [Patient type] = "Inpatient"))
Outpatients            = COUNTROWS(FILTER(df, [Patient type] = "outpatient"))
Total Staff            = DISTINCTCOUNT(Staff_Detail[Staff_Id])
Recorded Occ. Beds     = DISTINCTCOUNT(Bed_ID)   -- nulls excluded
Avg LOS                = AVERAGE(LOS)
Avg ER Time            = AVERAGE(ER_Time)         -- 719 nulls excluded
Avg Treatment Cost     = AVERAGE(treatemencost)
Total Revenue          = SUM(treatemencost)
Deaths                 = COUNTROWS(FILTER(df, [Status] = "Death"))
Discharges             = COUNTROWS(FILTER(df, [Status] = "Discharge"))
Readmissions           = COUNTROWS(FILTER(df, [Status] = "Readmit"))
Avg Rating             = AVERAGE(Rating)
```

### Derived Column Formulas

```
Occupied_Bed_Flag  = IF(ISBLANK(Bed_ID), 0, 1)
Readmission_Flag   = IF([Status] = "Readmit", 1, 0)
Prolonged_Stay     = IF([LOS] > 6, 1, 0)

Year               = YEAR(Date)
Month              = MONTH(Date)
Month_Name         = FORMAT(Date, "MMMM")
Week               = WEEKNUM(Date)
Quarter            = QUARTER(Date)
Day                = DAY(Date)
Day_Name           = FORMAT(Date, "dddd")
```

### Phase 2 Diagnostic Formulas

```
-- Category thresholds (adaptive per filtered slice)
Q33_ER   = PERCENTILE(ER_Time, 0.33)
Q66_ER   = PERCENTILE(ER_Time, 0.66)
Q33_LOS  = PERCENTILE(LOS, 0.33)
Q66_LOS  = PERCENTILE(LOS, 0.66)
Q33_Cost = PERCENTILE(treatemencost, 0.33)
Q66_Cost = PERCENTILE(treatemencost, 0.66)

-- Readmission rate
Readmission_Rate_% = (COUNTROWS(Status = "Readmit") / COUNTROWS(ALL)) × 100

-- Rate by group g
Rate(g) = (COUNTROWS(Status="Readmit" AND Group=g) / COUNTROWS(Group=g)) × 100

-- LOS vs Cost Pearson r
r = CORR(LOS, treatemencost)

-- Department group stats
Mean_LOS(D)      = AVERAGEIF(Dept=D, LOS)
Median_LOS(D)    = MEDIANIF(Dept=D, LOS)
Total_Revenue(D) = SUMIF(Dept=D, treatemencost)
Mean_Cost(D)     = AVERAGEIF(Dept=D, treatemencost)
```

---

## 14. Data Rules and Constraints

| Rule | Detail |
|---|---|
| No data generation | Zero synthetic values at any point |
| No Excel modification | File opened read-only; MD5 verified unchanged |
| No hardcoded KPI values | All values computed from the DataFrame at runtime |
| No silent record deletion | Invalid values → NaN; counts in QualityReport |
| No ML models | No training, no predictions |
| No diagnosis fabrication | Diagnosis absent → clearly stated unavailable |
| No absolute paths | All paths relative or runtime-resolved |
| No Pearson r on categoricals | Group stats used instead |
| Causation not claimed | Readmission patterns = "associated factors" |
| Filter-adaptive thresholds | Q33/Q66 recompute per filtered slice |
| PII excluded from display | `Name` column excluded from all dataframe views |

---

## 15. Validation Results

| Check | Expected | Result |
|---|---|---|
| Total Patients | 2,506 | ✅ |
| Inpatients | 1,679 | ✅ |
| Outpatients | 827 | ✅ |
| Total Staff | 262 | ✅ |
| Deaths | 86 | ✅ |
| Discharges | 209 | ✅ |
| Readmissions | 493 | ✅ |
| Readmission Rate | 19.7% | ✅ |
| ER count | 1,787 | ✅ |
| ER missing | 719 | ✅ |
| ER mean | 65.6 min | ✅ |
| ER median | 35.0 min | ✅ |
| LOS departments | 10 | ✅ |
| Total revenue | $404,488.14 | ✅ |
| Cardiology readmissions | 0 | ✅ |
| PMR readmission rate | 76.3% | ✅ |
| All 17 Phase 2 charts produce traces | — | ✅ |
| All 17 charts handle empty DataFrame | — | ✅ |
| Excel MD5 unchanged | `9921c00a29b7190f17ab2106830872d5` | ✅ |
| DIAGNOSIS_AVAILABLE | False | ✅ |

---

## 16. Known Limitations

| Limitation | Detail |
|---|---|
| Single year of data | Dataset covers 2007 only — year-over-year trends not possible |
| No Diagnosis column | Clinical cost analysis by diagnosis not feasible |
| ER_Time missingness | 28.7% of records (mostly Inpatients) have no ER_Time |
| Bed occupancy is historical | Reflects assignment records, not live occupancy |
| No forecasting | Phase 3 (Predictive Analytics) not yet implemented |
| LOS = 0 | 755 same-day/outpatient records with LOS=0 included in all LOS calculations |

---

*MediSight · Phases 1 and 2 complete · Generated from verified codebase*
