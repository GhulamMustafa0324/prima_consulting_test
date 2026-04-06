# Cashflow Calculation System

A Django web application that replaces an Excel-based actuarial cashflow model. It calculates the **Expected Death Outflow** for each employee — the statistical monetary cost if an employee dies before reaching retirement age.

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000

## Usage

1. **Upload** — Upload a CSV file with employee data
2. **Process** — Click "Run Calculation" to execute the model
3. **Download** — Download the output CSV from the result page
4. **History** — View all past executions at `/history/`

## Input CSV Format

```
emp_id,emp_name,date_birth,date_joining,salary
1,Employee 1,1989-02-07,2024-02-07,11280.25
```

| Column | Type | Notes |
|---|---|---|
| `emp_id` | Number or text | Must be unique |
| `emp_name` | Text | Employee full name |
| `date_birth` | Date (YYYY-MM-DD) | Must be before date_joining |
| `date_joining` | Date (YYYY-MM-DD) | Must be before valuation date |
| `salary` | Positive number | Current salary |

## Output CSV Format

```
emp_id,emp_name,age,future_salary,px,qx,expected_death_outflow
1,Employee 1,35,11280.25,0.9977105,0.0022895,25.767003
```

One row per employee per year from current age to retirement age (60).

## Calculation Logic

Replicates the Excel `calculation` sheet:

1. **Age** = `INT((valuation_date - date_birth + 1) / 365.25)`
2. **Future Salary** = `salary × (1 + 0.05) ^ years_ahead`
3. **px / qx** = looked up from `lookup_probability` mortality table
4. **Expected Death Outflow** = `future_salary × px × qx`

### Assumptions (pending client confirmation)

| Assumption | Value | Location |
|---|---|---|
| Valuation date | 2024-12-31 | `engine/constants.py` |
| Salary increase rate | 5% | `engine/constants.py` |
| Retirement age | 60 | `engine/constants.py` |
| Discount rate | 5.45% (not applied yet) | `engine/constants.py` |

## Running Tests

```bash
pip install pytest pytest-django
pytest tests/ -v
```

## Project Structure

```
cashflow_project/
├── calculator/
│   ├── engine/          # Calculation engine (zero Django dependency)
│   │   ├── calculator.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   └── mortality_table.py
│   ├── data/
│   │   └── mortality_table.csv
│   ├── templates/calculator/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── tests/
├── media/
└── manage.py
```
