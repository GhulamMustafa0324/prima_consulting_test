# All actuarial assumptions from the Excel input_assumptions sheet.
# Centralised here — changing a value only requires editing this file.
# ASSUMPTION: Hardcoded until client confirms whether these come from a CSV upload.

from datetime import date

VALUATION_DATE: date = date(2024, 12, 31)   # input_assumptions!B3
DISCOUNT_RATE: float = 0.0545               # input_assumptions!B4 — stubbed, not applied yet
SALARY_INCREASE_RATE: float = 0.05          # input_assumptions!B5
RETIREMENT_AGE: int = 60                    # input_assumptions!B6

REQUIRED_INPUT_COLUMNS: list[str] = [
    "emp_id", "emp_name", "date_birth", "date_joining", "salary",
]

OUTPUT_COLUMNS: list[str] = [
    "emp_id", "emp_name", "age", "future_salary", "px", "qx", "expected_death_outflow",
]

ALLOWED_UPLOAD_EXTENSION: str = ".csv"
MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
