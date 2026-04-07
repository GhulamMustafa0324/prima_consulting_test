# Core calculation engine — zero Django dependency.
# Takes an input CSV path, runs all calculations, writes output CSV.
#
# THE CALCULATION (replicates Excel calculation sheet):
#   For each employee:
#     1. Compute current age: INT((valuation_date - date_birth + 1) / 365.25)
#     2. For each year from current_age to RETIREMENT_AGE - 1:
#        a. future_salary = salary * (1 + SALARY_INCREASE_RATE) ^ years_ahead
#        b. px, qx = lookup from mortality table
#        c. expected_death_outflow = future_salary * px * qx
#
# ASSUMPTION: _apply_discount() is stubbed — not called until client confirms formula.

import math
import logging
import os

import pandas as pd
from dateutil import parser as date_parser

from calculator.engine.constants import (
    DISCOUNT_RATE,
    OUTPUT_COLUMNS,
    REQUIRED_INPUT_COLUMNS,
    RETIREMENT_AGE,
    SALARY_INCREASE_RATE,
    VALUATION_DATE,
)
from calculator.engine.exceptions import InputValidationError, OutputWriteError
from calculator.engine.mortality_table import MortalityTable

logger = logging.getLogger(__name__)


class CalculationEngine:

    def __init__(self) -> None:
        self._mortality_table = MortalityTable()

    def run(self, input_path: str, output_path: str) -> dict:
        """
        Full pipeline: validate → calculate → write output.
        Returns: {'input_rows': int, 'output_rows': int}
        Raises: InputValidationError, MortalityTableLookupError, OutputWriteError
        """
        df = self._load_and_validate(input_path)
        output_df = self._calculate(df)
        self._write_output(output_df, output_path)
        return {"input_rows": len(df), "output_rows": len(output_df)}

    # step 1: load and validate input CSV
    
    def _load_and_validate(self, input_path: str) -> pd.DataFrame:
        if not os.path.isfile(input_path):
            raise InputValidationError("Input file not found. This is a server error.")

        try:
            df = pd.read_csv(input_path, dtype=str, skipinitialspace=True)
        except pd.errors.EmptyDataError:
            raise InputValidationError("The uploaded CSV is empty.")
        except Exception as exc:
            raise InputValidationError(f"Could not parse CSV: {exc}")

        df.columns = [c.strip().lower() for c in df.columns]
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        df = df.dropna(how="all").reset_index(drop=True)

        if df.empty:
            raise InputValidationError("CSV has no data rows.")

        missing = set(REQUIRED_INPUT_COLUMNS) - set(df.columns)
        if missing:
            raise InputValidationError(f"Missing required columns: {sorted(missing)}.")

        df = self._validate_emp_id(df)
        df = self._validate_dates(df)
        df = self._validate_salary(df)
        df = self._compute_age(df)
        self._check_already_retired(df)
        return df

    def _validate_emp_id(self, df: pd.DataFrame) -> pd.DataFrame:
        if df["emp_id"].isnull().any() or (df["emp_id"] == "").any():
            raise InputValidationError("'emp_id' contains blank values.")
        if df["emp_id"].duplicated().any():
            dupes = df.loc[df["emp_id"].duplicated(keep=False), "emp_id"].tolist()
            raise InputValidationError(f"Duplicate emp_id values: {dupes}.")
        return df

    def _validate_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ("date_birth", "date_joining"):
            errors, parsed = [], []
            for idx, val in enumerate(df[col]):
                if pd.isnull(val) or val == "":
                    errors.append(f"Row {idx + 2}: '{col}' is blank.")
                    parsed.append(None)
                    continue
                try:
                    parsed.append(date_parser.parse(str(val)).date())
                except (ValueError, OverflowError):
                    errors.append(f"Row {idx + 2}: '{col}' value '{val}' is not a valid date.")
                    parsed.append(None)
            if errors:
                raise InputValidationError(f"Date errors in '{col}':\n" + "\n".join(errors))
            df[col] = parsed

        bad_order = df[df["date_birth"] >= df["date_joining"]]["emp_id"].tolist()
        if bad_order:
            raise InputValidationError(f"date_birth >= date_joining for emp_id(s): {bad_order}.")

        future_dob = df[df["date_birth"] >= VALUATION_DATE]["emp_id"].tolist()
        if future_dob:
            raise InputValidationError(
                f"date_birth is on or after valuation date for emp_id(s): {future_dob}."
            )
        return df

    def _validate_salary(self, df: pd.DataFrame) -> pd.DataFrame:
        errors, parsed = [], []
        for idx, val in enumerate(df["salary"]):
            if pd.isnull(val) or val == "":
                errors.append(f"Row {idx + 2}: 'salary' is blank.")
                parsed.append(None)
                continue
            try:
                s = float(val)
                if not math.isfinite(s) or s <= 0:
                    raise ValueError
                parsed.append(s)
            except ValueError:
                errors.append(f"Row {idx + 2}: 'salary' must be a positive number. Got '{val}'.")
                parsed.append(None)
        if errors:
            raise InputValidationError("Salary errors:\n" + "\n".join(errors))
        df["salary"] = parsed
        return df

    def _compute_age(self, df: pd.DataFrame) -> pd.DataFrame:
        # Matches Excel formula: INT((valuation_date - date_birth + 1) / 365.25)
        df["current_age"] = df["date_birth"].apply(
            lambda dob: math.floor(((VALUATION_DATE - dob).days + 1) / 365.25)
        )
        return df

    def _check_already_retired(self, df: pd.DataFrame) -> None:
        retired = df[df["current_age"] >= RETIREMENT_AGE]["emp_id"].tolist()
        if retired:
            logger.warning("emp_id(s) already at retirement age, will produce 0 rows: %s", retired)

    # step 2: perform calculations
    def _calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, emp in df.iterrows():
            rows.extend(self._calculate_employee(emp))
        return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    def _calculate_employee(self, emp: pd.Series) -> list[dict]:
        rows = []
        base_salary = float(emp["salary"])
        current_age = int(emp["current_age"])

        for years_ahead, age in enumerate(range(current_age, RETIREMENT_AGE)):
            mortality = self._mortality_table.lookup(age)
            future_salary = base_salary * ((1 + SALARY_INCREASE_RATE) ** years_ahead)
            px, qx = mortality["px"], mortality["qx"]

            rows.append({
                "emp_id":                 emp["emp_id"],
                "emp_name":               emp["emp_name"],
                "age":                    age,
                "future_salary":          round(future_salary, 6),
                "px":                     round(px, 7),
                "qx":                     round(qx, 7),
                "expected_death_outflow": round(future_salary * px * qx, 6),
            })
        return rows

    @staticmethod
    def _apply_discount(outflow: float, years_ahead: int) -> float:
        # STUBBED — not called until client confirms discounting formula.
        # Formula: outflow / (1 + DISCOUNT_RATE) ^ years_ahead
        return outflow if years_ahead == 0 else outflow / ((1 + DISCOUNT_RATE) ** years_ahead)

    # step 3: write output CSV
    def _write_output(self, output_df: pd.DataFrame, output_path: str) -> None:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            output_df.to_csv(output_path, index=False)
        except OSError as exc:
            raise OutputWriteError(f"Could not write output CSV: {exc}") from exc
