# Cashflow Calculator

A Django web app that takes employee data as a CSV and calculates the expected death benefit outflow for each employee — year by year — until retirement.

---

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000

---

## How to Use

1. Go to the home page and upload a CSV file
2. Click **Run Calculation**
3. Download the output CSV from the result page
4. All past runs are saved at `/history/`

---

## Input CSV

Your CSV must have these exact columns:

| Column | Example |
|---|---|
| emp_id | 1 |
| emp_name | Employee 1 |
| date_birth | 1989-02-07 |
| date_joining | 2024-02-07 |
| salary | 11280.25 |

---

## Output CSV

One row per employee per year, from their current age up to retirement (age 60):

| Column | What it means |
|---|---|
| emp_id | Employee ID |
| emp_name | Employee name |
| age | Age in that projection year |
| future_salary | Salary projected forward at 5% per year |
| px | Probability of surviving to this age |
| qx | Probability of dying at this age |
| expected_death_outflow | future_salary × px × qx |

---

## The Calculation

For each employee, for each year from their current age to 59:

```
future_salary  = current_salary × (1.05 ^ years_ahead)
px, qx         = looked up from mortality table by age
outflow        = future_salary × px × qx
```

This replicates the Excel `calculation` sheet exactly.

---

## Assumptions

These are hardcoded in `calculator/engine/constants.py` and match the Excel `input_assumptions` sheet:

| Setting | Value |
|---|---|
| Valuation date | 2024-12-31 |
| Salary increase rate | 5% per year |
| Retirement age | 60 |
| Discount rate | 5.45% |

---

## Project Structure

```
cashflow_project/
├── calculator/
│   ├── engine/
│   │   ├── constants.py        # All assumptions in one place
│   │   ├── exceptions.py       # Custom error types
│   │   ├── mortality_table.py  # Loads age → qx/px lookup table
│   │   └── calculator.py       # Core calculation logic
│   ├── data/
│   │   └── mortality_table.csv # Age probability data (from Excel)
│   ├── templates/              # HTML pages
│   ├── models.py               # Execution history table
│   ├── views.py                # Upload, Process, Result, History, Download
│   ├── forms.py                # File upload validation
│   └── urls.py
└── tests/
    ├── test_calculator.py
    ├── test_mortality_table.py
    ├── test_forms.py
    └── test_views.py
```

---

## Running Tests

```bash
pip install pytest pytest-django
pytest tests/ -v
```

43 tests, all passing.