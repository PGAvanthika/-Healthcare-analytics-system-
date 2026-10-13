# MediSight — Technical Documentation

**Healthcare Analytics & Decision Support System**
Phases 1, 2, and 3 — Python · Streamlit · Pandas · Plotly

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Data Source and Schema](#4-data-source-and-schema)
5. [Data Processing](#5-data-processing)
6. [Global Sidebar Filters](#6-global-sidebar-filters)
7. [Feature 1 — Expected LOS Prediction](#7-feature-1--expected-los-prediction)
8. [Feature 2 — Bed Demand Forecasting](#8-feature-2--bed-demand-forecasting)
9. [Diagnostic Analytics](#9-diagnostic-analytics)
10. [KPI Definitions](#10-kpi-definitions)
11. [Validation and Testing](#11-validation-and-testing)
12. [Limitations and Future Work](#12-limitations-and-future-work)

---

## 1. Project Overview

MediSight is a Streamlit-based healthcare analytics and decision-support application that reads a single Excel workbook and computes all analytics in memory. No data is generated, no files are written, and the original Excel file is never modified.

**Objectives:**
- Provide hospital managers with dynamic KPI monitoring and exploratory data analytics
- Surface diagnostic patterns (readmissions, ER wait times, LOS, treatment costs)
- Forecast inpatient arrivals and estimate average bed requirements using statistical baselines
- Serve as an extensible foundation for future predictive features

**Implementation Status:**

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Complete | Data loading, preprocessing, 13 KPIs, 5 overview charts, data quality panel |
| Phase 2 | ✅ Complete | Diagnostic Analytics — 4 modules, 17 Plotly charts |
| Phase 3 — Feature 1 | ✅ Complete | Expected LOS Prediction (historical median) |
| Phase 3 — Feature 2 | ✅ Complete | Bed Demand Forecasting (SES + Expected LOS) |

---

## 2. Technology Stack

| Library | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime |
| Streamlit | 1.65.0 | Web UI framework, navigation, caching |
| Pandas | 3.0.6 | All data manipulation and aggregation |
| NumPy | 2.4.6 | Numeric operations, SES implementation |
| Plotly | 7.1.0 | All interactive charts |
| OpenPyXL | 3.1.5 | Excel file reading (`engine="openpyxl"`) |
| pyarrow | 25.0.1 | Arrow backend for Pandas |
| altair | 6.3.0 | Streamlit dependency (not used directly) |

**No machine-learning libraries are used.** SES is implemented from scratch in NumPy. No model training, no synthetic data generation.

---

## 3. Project Structure

```
medisight/
├── app.py                     # Entry point — all pages, sidebar, router (~1700 lines)
├── config.py                  # All constants: column names, sheet names, thresholds
├── requirements.txt           # Pinned dependencies
├── .gitignore
├── TECHNICAL_DOCUMENTATION.md
│
├── data/
│   └── Hospital  Health Care Management Data set.xlsx   # Source of truth
│
├── utils/
│   ├── __init__.py
│   ├── data_loader.py         # @st.cache_data Excel readers, one per sheet
│   ├── preprocessing.py       # 8-step preprocessing pipeline, QualityReport
│   ├── metrics.py             # 13-KPI engine (calculate_kpis)
│   ├── descriptive.py         # Phase 1 — 5 overview Plotly chart functions
│   ├── diagnostic.py          # Phase 2 — 4 modules, 17 chart functions
│   └── predictive.py          # Phase 3 — Feature 1 (LOS) + Feature 2 (Bed Demand)
│
├── assets/                    # Reserved for static assets (currently empty)
└── pages/                     # Reserved for future multi-page expansion (empty)
```

### Module responsibilities

| Module | Responsibility |
|---|---|
| `app.py` | Page config, CSS, data loading, sidebar (nav + filters), filter application, KPI calculation, page routing, all render_* functions |
| `config.py` | Single source of truth for all string constants (column names, sheet names, status values, thresholds) |
| `utils/data_loader.py` | Excel reading with `@st.cache_data`, path resolution, one function per sheet |
| `utils/preprocessing.py` | Column cleaning, type conversion, validation, department enrichment, derived features, `QualityReport` |
| `utils/metrics.py` | `calculate_kpis(filtered_df, staff_df, bed_df)` → `KPIResult` dataclass |
| `utils/descriptive.py` | 5 Plotly chart functions for Phase 1 Patient Overview |
| `utils/diagnostic.py` | Threshold helpers, 4 diagnostic modules (A–D), 17 chart functions |
| `utils/predictive.py` | Feature 1: LOS estimation functions; Feature 2: SES engine, bed demand, 3 chart functions |

---

## 4. Data Source and Schema

**File:** `data/Hospital  Health Care Management Data set.xlsx`
(Double space in filename is intentional — matches the original.)

This is the **single source of truth**. The file is opened read-only via `pd.read_excel(..., engine="openpyxl")` and its MD5 hash (`9921c00a29b7190f17ab2106830872d5`) remains unchanged after every run.

### Workbook Sheets

| Sheet Name | Rows | Columns | Purpose |
|---|---|---|---|
| `Detail data dataset` | 2,506 | 21 | Main patient records |
| `Staff_Detail` | 262 | 2 | Staff dimension |
| `Department` | 10 | 2 | Department lookup |
| `Bed_Detail` | 2,847 | 2 | Bed records |

### Patient Dataset Columns

| Column | Type | Nulls | Notes |
|---|---|---|---|
| `Staff_Id` | int64 | 0 | FK to Staff_Detail |
| `Bed_ID` | float64 | 755 | Null = no bed assigned (outpatients) |
| `Dpt_ID` | int64 | 0 | FK to Department |
| `ID` | int64 | 0 | Patient ID — 2,506 unique (max 4,126) |
| `Name` | str | 0 | PII — excluded from all display tables |
| `Gender` | str | 0 | `F`, `M` |
| `City` | str | 0 | 16 unique values |
| `State` | str | 0 | 37 unique values |
| `Age` | int64 | 0 | Range: 1–98 |
| `Patient type` | str | 0 | `Inpatient`, `outpatient` (lowercase 'o') |
| `Status` | str | 0 | `Normal`, `Readmit`, `Discharge`, `ICU`, `Death` |
| `treatemencost` | float64 | 0 | Range: $2.54–$1,241.33 per patient |
| `Bed` | str | 755 | Only value: `Occupied` |
| `LOS` | int64 | 0 | Range: 0–32 days |
| `ER_Time` | float64 | 719 | Range: 11–190 minutes (mostly Inpatients missing) |
| `Date` | datetime64 | 0 | Range: 2007-01-01 to 2007-12-31 |
| `Feedback` | str | 0 | 5 Likert values |
| `Rating` | float64 | 0 | Scale: 1.0–5.0 |
| `Age Bucket` | str | 0 | `Below 6Y`, `6-20Y`, `21-40Y`, `41-60y`, `60+Y` |
| `Custom` | str | 0 | LOS bucket label (text) |
| `FZ me` | str | 0 | Sentiment: Positive / Negative / Neutral |

### Status Distribution (full dataset)

| Status | Count | % |
|---|---|---|
| Normal | 1,636 | 65.3% |
| Readmit | 493 | 19.7% |
| Discharge | 209 | 8.3% |
| Death | 86 | 3.4% |
| ICU | 82 | 3.3% |

### Date Semantics (confirmed)

Each `(patient_id, date)` pair is unique across all 2,506 records. Multiple patients share the same calendar date (max 77 per day). This is consistent with `Date` representing an admission or encounter date — suitable for time-series aggregation.

### Department Join

The Department sheet (10 rows, one per Dpt_ID) joins safely to the patient table: all 2,506 patient rows match exactly one department, and the row count does not change after the merge.

---

## 5. Data Processing

### Loading

`utils/data_loader.py` provides one `@st.cache_data`-decorated function per sheet (`load_patient_data`, `load_staff_data`, `load_department_data`, `load_bed_data`) and a combined `load_all_data()` wrapper. The Excel path is resolved relative to the project root; no absolute paths are used.

### Preprocessing Pipeline (`utils/preprocessing.py`)

Runs once per session (cached). Returns `(processed_df, QualityReport)`.

| Step | Function | Action |
|---|---|---|
| 1 | `_clean_column_names` | Strip whitespace from column names |
| 2 | `_normalise_empty_strings` | Replace `""` / whitespace-only strings → `NaN` |
| 3 | `_validate_dates` | Parse `Date` with `errors="coerce"` → invalid → `NaT` |
| 4 | `_validate_numerics` | Coerce 5 numeric columns; out-of-range → `NaN` |
| 5 | `_check_duplicates` | Count fully duplicate rows (retained, not dropped) |
| 6 | `_audit_missing` | Record null counts per column |
| 7 | `_enrich_with_department` | Safe left-join to add `Department_Name` |
| 8 | `_add_derived_features` | Add 10 runtime-only derived columns |

**Numeric validation ranges:**

| Column | Min | Max |
|---|---|---|
| `Age` | 0 | 120 |
| `treatemencost` | 0.0 | None |
| `LOS` | 0 | 365 |
| `ER_Time` | 0 | 1,440 |
| `Rating` | 1 | 5 |

**Derived columns (in-memory only, never written to Excel):**

| Column | Formula | Source |
|---|---|---|
| `Year` | `Date.dt.year` | `Date` |
| `Month` | `Date.dt.month` | `Date` |
| `Month_Name` | `Date.dt.strftime("%B")` | `Date` |
| `Week` | `Date.dt.isocalendar().week` | `Date` |
| `Quarter` | `Date.dt.quarter` | `Date` |
| `Day` | `Date.dt.day` | `Date` |
| `Day_Name` | `Date.dt.strftime("%A")` | `Date` |
| `Occupied_Bed_Flag` | `1 if Bed_ID is not NaN else 0` | `Bed_ID` |
| `Readmission_Flag` | `1 if Status == "Readmit" else 0` | `Status` |
| `Prolonged_Stay` | `1 if LOS > 6 else 0` | `LOS` |

### Caching Behaviour

`_load_and_preprocess()` in `app.py` is decorated with `@st.cache_data(show_spinner=False)`. It runs once per session. All `render_*` page functions read the cached `processed_df` and `filtered_df` from the module scope — no re-reading on filter changes.

---

## 6. Global Sidebar Filters

All sidebar widgets are rendered inside `with st.sidebar:` at the top of `app.py`. Filter variables are module-level and shared by all page renderers as closures.

### Filters Available

| Widget | Variable | Default | Type |
|---|---|---|---|
| Date "From" | `date_from` | `min_date` (2007-01-01) | `datetime.date` |
| Date "To" | `date_to` | `max_date` (2007-12-31) | `datetime.date` |
| Department | `selected_depts` | `[]` (all) | `list[str]` |
| Patient Type | `selected_types` | `[]` (all) | `list[str]` |

### Date Range Validation

If `date_from > date_to`, an error banner is shown in the sidebar and the dates are swapped so that the app continues to render with a valid (non-empty) range. The user must correct the selection to get the intended results.

### How `filtered_df` is Built

```python
filtered_df = processed_df.copy()

# Date range
filtered_df = filtered_df[
    (filtered_df["Date"].dt.date >= date_from) &
    (filtered_df["Date"].dt.date <= date_to)
]

# Department (only applied if at least one is selected)
if selected_depts:
    filtered_df = filtered_df[filtered_df["Department_Name"].isin(selected_depts)]

# Patient type (only applied if at least one is selected)
if selected_types:
    filtered_df = filtered_df[filtered_df["Patient type"].isin(selected_types)]
```

`filtered_df` is a module-level variable computed after the sidebar block. Every page renderer reads it directly without requiring it as a parameter.

### Pages and Calculations Affected

| Filter | Dataset Overview | Hospital KPIs | Patient Overview | Diagnostic Analytics | Expected LOS | Bed Demand |
|---|---|---|---|---|---|---|
| Date Range | ❌ (shows raw) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Department | ❌ (shows raw) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Patient Type | ❌ (shows raw) | ✅ | ✅ | ✅ | ✅ | ✅ inpatient-only† |

† The Bed Demand section further restricts to `Patient type == "Inpatient"` regardless of the Patient Type filter. This is intentional: bed demand forecasting is based on inpatient arrivals only.

**Dataset Overview** uses `processed_df` (full unfiltered data) for dataset-structure information (row counts, column types, date range, quality report). It uses `kpis` (which is based on `filtered_df`) for the "Total Staff" stat card.

### Empty Results Handling

If the applied filters produce an empty `filtered_df`, each page renderer shows a `st.warning()` message and returns early. No errors or tracebacks are exposed to the user.

### Additional Filters (Planned)

The sidebar contains a collapsed "More filters — Phase 3+" expander with four disabled placeholders (Gender, Age Group, Status, City). These are not yet functional.

---

## 7. Feature 1 — Expected LOS Prediction

**Location:** `utils/predictive.py` · Rendered in `render_predictive_analytics()` sections 1–4

**Method:** Historical median-based group estimation. No ML model is trained.

### Rationale for the Median

LOS data is right-skewed (755 records with LOS = 0; max = 32 days). The median is more robust to extreme outliers than the mean and gives a better "typical stay" estimate for clinical planning.

### Grouping Hierarchy

`estimate_los(df, department, patient_type, age_bucket)` tries the following levels from most to least specific, returning the first level that has at least one valid record:

| Level | Condition | Label |
|---|---|---|
| 1 (most specific) | dept + type + age | "Department + Patient Type + Age Bucket" |
| 2 | dept + type | "Department + Patient Type" |
| 3 | dept only | "Department" |
| **4 (new)** | **type only** | **"Patient Type (Inpatient)"** |
| 5 (fallback) | none | "Overall (all records)" |

Level 4 was added to fix a bug where `estimate_los(df, None, "Inpatient", None)` was silently using all 2,506 records instead of the correct 1,679 inpatient records. The fix ensures the patient-type filter is honoured even when no department is selected.

### Formulas

```
Expected LOS(group) = MEDIAN(LOS WHERE group conditions AND LOS IS NOT NULL)
Mean LOS(group)     = AVERAGE(LOS WHERE group conditions AND LOS IS NOT NULL)
```

### Minimum Records Flag

Groups with fewer than 5 records (`MIN_GROUP_RECORDS = 5`) are flagged as low-confidence with a ⚠ indicator in the results table and an amber card background. The estimate is shown but clearly caveated.

### Validated Baseline Values (full unfiltered dataset)

| Group | Median LOS | Records |
|---|---|---|
| All patients (Overall) | 2.0 days | 2,506 |
| Inpatient only | 2.0 days | 1,679 |
| outpatient only | 0.0 days | 827 |
| Surgery / Inpatient | 2.0 days | 436 |
| OPD / outpatient | 0.0 days | 824 |
| PMR / Inpatient | 2.0 days | 515 |

### Functions

| Function | Description |
|---|---|
| `overall_los_stats(df)` | Median, mean, std, min, max, valid count, dept count |
| `los_by_department(df)` | Per-department LOS stats table |
| `los_by_dept_type(df)` | Per (dept × type) LOS stats table |
| `los_by_dept_type_age(df)` | Per (dept × type × age bucket) LOS stats table |
| `estimate_los(df, dept, type, age)` | Single-group estimate with fallback |
| `plot_median_los_by_department(df)` | H-bar chart: median LOS per dept |
| `plot_median_los_by_dept_type(df)` | Grouped H-bar: median LOS by dept & type |
| `plot_los_distribution_by_type(df)` | Overlapping histogram by patient type |

### UI Sections

1. **Overall LOS Summary** — 4 KPI cards
2. **Group Selector & Expected LOS** — 3 dropdowns (dept, type, age) + live estimate card
3. **Results Table** — Dept · Patient Type · Age Bucket · Expected LOS · Mean · Min · Max · Records
4. **Visualisations** — 2 chart pairs

---

## 8. Feature 2 — Bed Demand Forecasting

**Location:** `utils/predictive.py` · Rendered in `render_predictive_analytics()` section 5

**Method:** Simple Exponential Smoothing (SES) on weekly inpatient arrivals + Expected LOS from Feature 1.

### Admission-Date Validation (confirmed)

- Each `(patient_id, date)` pair is unique across all 2,506 records ✓
- Multiple patients share the same calendar date (up to 77 per day) ✓
- Date column has zero nulls and is datetime type ✓
- Conclusion: `Date` is a valid admission/encounter date suitable for arrival counting

### Inpatient Arrival Aggregation

Only `Patient type == "Inpatient"` records are counted (1,679 total). Weekly aggregation is used:

```
weekly_count(Year=Y, Week=W) = COUNT(rows WHERE Patient type='Inpatient'
                                           AND Year=Y AND Week=W)
```

The result is a 52-observation time series for 2007 with no zero-weeks (CV ≈ 1.12). The input `filtered_df` already has the global date range and department filters applied before this function is called.

### SES Implementation

SES is implemented from scratch in NumPy (`_ses_smooth`, `_ses_forecast`, `_find_best_alpha`). No external forecasting library is required.

**Smoothing equation:**

```
S(0) = Y(0)
S(t) = α × Y(t) + (1 − α) × S(t−1)
```

Where:
- `Y(t)` = observed weekly inpatient arrivals for period t
- `S(t−1)` = previous smoothed level
- `α` = smoothing parameter (0, 1]

**All h-step-ahead forecasts are flat/constant** — equal to the last smoothed value. SES does not model trend or seasonality.

### Alpha Selection

Grid search over α ∈ {0.05, 0.10, …, 0.95}, minimising holdout MSE on the last `max(4, n//5)` observations (~20% of series). Alpha is chosen on the **training portion only** — future observations are never used for selection (no leakage).

```
holdout_n = max(4, n // 5)       # = 10 for full 52-week series
train     = series[: n - holdout_n]
test      = series[n - holdout_n :]

For each alpha:
    fitted_train = _ses_smooth(train, alpha)
    pred_test    = full(holdout_n, fitted_train[-1])   # constant forecast
    MSE          = mean((test − pred_test)²)

best_alpha = argmin(MSE)
```

**Optimised alpha on full dataset: 0.75** (more weight on recent observations)

### Accuracy Metrics

Calculated on the holdout period (last 10 weeks for the full dataset):

```
RMSE = √(mean((actual − predicted)²))
MAE  = mean(|actual − predicted|)
```

**Baseline comparisons** are also computed and displayed:

| Model | Holdout RMSE | Holdout MAE |
|---|---|---|
| SES (α=0.75) | **4.99** | **4.15** |
| Naïve (last observed) | 5.08 | 4.20 |
| Historical mean | 25.32 | 24.87 |

SES outperforms both baselines on this dataset. The improvement over naïve is modest (SES RMSE 4.99 vs naïve 5.08), which is expected for a high-variance series with no strong trend.

### Expected LOS Integration

`estimate_los(df, department, "Inpatient", None)` is called directly — the same function as Feature 1, with `patient_type="Inpatient"` to use only inpatient records for the LOS estimate. This ensures consistency with Feature 1 and honours the patient-type filter fix.

If the department-level estimate has insufficient data (< 5 records), the function falls back to the patient-type-only level (1,679 inpatient records), then to the overall median.

### Bed Demand Formula

**Stage A — Convert weekly forecast to daily:**

```
Forecast Daily Arrivals = Forecast Weekly Arrivals / 7
```

**Stage B — Steady-flow approximation:**

```
Estimated Average Bed Demand ≈ Forecast Daily Arrivals × Expected LOS (days)
```

Example from validated full dataset:
- Forecast weekly = 9.0 inpatients/week
- Forecast daily = 9.0 / 7 = 1.2857/day
- Expected LOS (Inpatient) = 2.0 days
- Estimated avg bed demand = 1.2857 × 2.0 ≈ **2.57 beds**

This approximation is valid when admission and discharge flows are in approximate steady state. It represents **average concurrent occupancy**, not daily peak or guaranteed capacity.

### Limitations

- Single year of data (2007): seasonal patterns cannot be validated cross-year
- High week-to-week variance (CV ≈ 1.1): uncertainty intervals are material
- SES improvement over naïve is small for this dataset
- No operational bed capacity data available — occupancy % cannot be calculated
- The forecast is a statistical baseline, not a guaranteed future outcome

### Functions

| Function | Description |
|---|---|
| `validate_date_semantics(df)` | Checks datetime type, nulls, (ID, date) uniqueness |
| `build_weekly_inpatient_series(df, department)` | Inpatient-only weekly count series |
| `_ses_smooth(series, alpha)` | Pure NumPy SES smoothing |
| `_ses_forecast(series, alpha, horizon)` | Flat constant forecast |
| `_find_best_alpha(series)` | Grid-search alpha on chronological holdout |
| `run_ses_forecast(df, department, horizon_weeks)` | Full pipeline → dict with RMSE, MAE, baselines |
| `estimate_bed_demand(forecast_daily, expected_los)` | Steady-flow bed demand |
| `department_bed_demand_table(df, horizon_weeks)` | Per-dept comparison table |
| `plot_ses_forecast(ses_result, horizon_weeks, label)` | History + SES fit + forecast chart |
| `plot_holdout_validation(ses_result)` | Actual vs predicted on holdout |
| `plot_bed_demand_bar(dept_table)` | H-bar: avg bed demand by dept |

---

## 9. Diagnostic Analytics

**Location:** `utils/diagnostic.py` · Rendered in `render_diagnostic_analytics()`

All functions accept `filtered_df` (already filtered by global sidebar). All thresholds are computed from the passed DataFrame using quantiles (Q33/Q66), so they adapt automatically to filter changes.

### Module A — Readmission Analysis

**Readmission Rate formula:**

```
Readmission Rate (%) = COUNT(Status == "Readmit") / COUNT(all rows) × 100

Rate(group g) = COUNT(Status == "Readmit" WHERE group=g)
                ──────────────────────────────────────── × 100
                COUNT(all rows WHERE group=g)
```

Applied to: Department, Patient Type, Age Group, ER Wait Category, LOS Category, Cost Category.

Baseline (full dataset): 493 readmissions / 2,506 total = **19.7%**

Notable finding: Physical Medicine & Rehabilitation Dept has 76.3% readmission rate (393/515).

**Labelling:** Readmission patterns are presented as "associated factors" — causation is not claimed.

### Module B — ER Wait-Time Analysis

- 1,787 records have valid ER_Time; 719 are null (mostly Inpatients)
- Adaptive category thresholds using Q33/Q66 of valid ER_Time values in the current filter
- Full-dataset thresholds: Short ≤ 35 min, Moderate 35–60 min, Long > 60 min
- Summary statistics: mean = 65.6 min, median = 35.0 min, std = 52.1 min

### Module C — LOS vs Department

- Department is categorical → Pearson correlation with department names is not used
- Per-department group statistics are computed instead (count, mean, median, min, max, std)
- Pearson r **is** calculated between LOS and treatment cost (both numeric) and shown on the scatter chart title

### Module D — Treatment Cost Analysis

- **No Diagnosis column exists** in any workbook sheet
- A prominent `st.info()` banner states this clearly in the UI
- Analysis uses Department as the clinical grouping variable, clearly labelled as such
- `DIAGNOSIS_AVAILABLE = False` constant prevents any accidental assumption of diagnosis data

**Total treatment revenue (full dataset): $404,488.14**

---

## 10. KPI Definitions

All 13 KPIs are computed in `utils/metrics.py` via `calculate_kpis(filtered_df, staff_df, bed_df)`.

| KPI | Formula | Source |
|---|---|---|
| Total Patients | `DISTINCTCOUNT(ID)` | `filtered_df` |
| Inpatients | `COUNT(Patient type == "Inpatient")` | `filtered_df` |
| Outpatients | `COUNT(Patient type == "outpatient")` | `filtered_df` |
| Total Staff | `DISTINCTCOUNT(Staff_Id)` on `staff_df` | `staff_df` (unfiltered) |
| Recorded Occupied Beds | `DISTINCTCOUNT(Bed_ID)` where Bed_ID not null | `filtered_df` |
| Avg LOS | `AVERAGE(LOS)` excl. NaN | `filtered_df` |
| Avg ER Time | `AVERAGE(ER_Time)` excl. NaN (719 nulls) | `filtered_df` |
| Avg Treatment Cost | `AVERAGE(treatemencost)` | `filtered_df` |
| Total Revenue | `SUM(treatemencost)` | `filtered_df` |
| Deaths | `COUNT(Status == "Death")` | `filtered_df` |
| Discharges | `COUNT(Status == "Discharge")` | `filtered_df` |
| Readmissions | `COUNT(Status == "Readmit")` | `filtered_df` |
| Avg Rating | `AVERAGE(Rating)` excl. NaN | `filtered_df` |

**Total Staff** uses `staff_df` (the unfiltered Staff_Detail dimension table) rather than `filtered_df`, because staff members exist independently of the patient date/department filter window.

**Validated baseline values (full unfiltered dataset):**

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

## 11. Validation and Testing

All validation was performed by running `_validate_final.py` (now deleted) against the real Excel workbook. The following checks passed.

### Compilation and Import Checks
- `app.py` compiles without syntax errors ✓
- `utils/predictive.py` compiles without syntax errors ✓
- All exported symbols from `utils/predictive.py` importable ✓

### Phase 1 / 2 KPI Regression (7 values verified on every run)

| Check | Expected | Result |
|---|---|---|
| Total Patients | 2,506 | ✅ |
| Inpatients | 1,679 | ✅ |
| Outpatients | 827 | ✅ |
| Deaths | 86 | ✅ |
| Discharges | 209 | ✅ |
| Readmissions | 493 | ✅ |
| Total Staff | 262 | ✅ |

### Feature 1 Fix — Patient-Type Filter

| Check | Before Fix | After Fix |
|---|---|---|
| `estimate_los(df, None, "Inpatient", None)` records | 2,506 (bug) | 1,679 ✅ |
| `estimate_los(df, None, "outpatient", None)` records | 2,506 (bug) | 827 ✅ |
| `estimate_los(df, "Surgery", "Inpatient", None)` records | 436 | 436 ✅ |
| Overall fallback (`None, None, None`) records | 2,506 | 2,506 ✅ |

### Feature 2 Accuracy Metrics

| Metric | Value | Recalculated Match |
|---|---|---|
| SES alpha | 0.75 | ✅ |
| Holdout RMSE | 4.99 | ✅ |
| Holdout MAE | 4.15 | ✅ |
| Naïve RMSE | 5.08 | ✅ |
| Historical mean RMSE | 25.32 | ✅ |
| SES better than naïve | Yes | ✅ |
| SES better than mean | Yes | ✅ |

### Weekly Series Aggregation

| Check | Expected | Result |
|---|---|---|
| Total weekly observations | 52 | ✅ |
| Total inpatients across all weeks | 1,679 | ✅ |
| Zero-count weeks | 0 | ✅ |
| Surgery weekly sum | 436 | ✅ |

### SES Math Unit Tests

- `_ses_smooth(series, alpha=1.0)` reproduces original series ✅
- S(0), S(1), S(2) computed manually and verified ✅
- `_ses_forecast` returns constant (flat) array for any horizon ✅

### Date Range Validation

- `date_from > date_to` triggers error banner and swap ✅
- Q1 2007 filter returns 1,175 records ✅
- Cardiology filter returns 48 records ✅

### Filter Correctness

- `Patient type == "Inpatient"`: 1,679 records ✅
- `Patient type == "outpatient"`: 827 records ✅
- SES on H1 filter: 730 inpatients, 13 weekly observations ✅

### Missing Data and Empty DataFrame Safety

- `overall_los_stats({})` returns `{}` ✅
- `estimate_los(empty, ...)` returns `no_data=True` ✅
- `run_ses_forecast(empty)` returns `success=False` ✅
- All chart functions handle empty DataFrame without exception ✅

### Excel Integrity

- MD5 hash `9921c00a29b7190f17ab2106830872d5` verified unchanged after every run ✅
- No CSV, Excel, or database write operations at any point ✅

### Streamlit Smoke Test

- `streamlit run app.py` starts without errors ✅
- HTTP 200 confirmed via `curl http://localhost:8502/` ✅
- No Python exceptions in server log ✅

---

## 12. Limitations and Future Work

### Confirmed Limitations

| Limitation | Detail |
|---|---|
| Single year of data | Dataset covers 2007 only — year-over-year trends and seasonal validation are not possible |
| ER_Time missingness | 28.7% of records (mostly Inpatients) have no ER_Time — ER analysis covers a subset |
| Bed occupancy is historical | `Recorded Occupied Beds` reflects bed assignment records, not live point-in-time occupancy |
| No Diagnosis column | Clinical cost analysis by diagnosis is not feasible from this workbook |
| SES model flatness | All h-step-ahead SES forecasts are equal (flat/constant) — no trend or seasonality modelled |
| SES uncertainty | Week-to-week variance is high (CV ≈ 1.1); the improvement over a naïve baseline is modest |
| No bed capacity data | Operational bed capacity is not in the workbook — occupancy percentage cannot be calculated |
| LOS = 0 records | 755 same-day/outpatient records have LOS = 0, which is included in all LOS statistics |

### Completed Features

- Phase 1: Data loading, preprocessing, 13 KPIs, 5 overview charts, data quality report
- Phase 2: Diagnostic Analytics — 4 modules (Readmission, ER, LOS, Cost), 17 charts
- Phase 3 Feature 1: Expected LOS Prediction (historical median, group hierarchy, fallback)
- Phase 3 Feature 2: Bed Demand Forecasting (SES, MAE/RMSE, baseline comparison, department table)

### Planned Future Work

- Additional sidebar filters: Gender, Age Group, Status, City
- Trend modelling (Holt's double exponential smoothing) if multi-year data becomes available
- Readmission risk scoring using logistic regression or gradient boosting
- Treatment cost estimation by patient profile
- Multi-year data integration for seasonal decomposition

---

*MediSight · Phases 1, 2, and 3 complete · Last updated after validation run confirming all checks passed*
