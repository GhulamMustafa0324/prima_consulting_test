import math
import os
import tempfile

import pandas as pd
import pytest

from calculator.engine.calculator import CalculationEngine
from calculator.engine.constants import RETIREMENT_AGE, SALARY_INCREASE_RATE, VALUATION_DATE
from calculator.engine.exceptions import InputValidationError, OutputWriteError


VALID_CSV = (
    "emp_id,emp_name,date_birth,date_joining,salary\n"
    "1,Employee 1,1989-02-07,2024-02-07,11280.25\n"
    "2,Employee 2,2001-04-08,2024-06-02,8029.80\n"
)


def _write_csv(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    f.write(content)
    f.close()
    return f.name


def _output_path() -> str:
    return os.path.join(tempfile.mkdtemp(), "output.csv")


@pytest.fixture
def engine():
    return CalculationEngine()


class TestAgeComputation:

    def test_age_matches_excel_formula(self, engine):
        # Excel: INT((valuation_date - date_birth + 1) / 365.25)
        # Employee 1: DOB 1989-02-07, valuation 2024-12-31 → age 35
        from datetime import date
        dob = date(1989, 2, 7)
        expected = math.floor(((VALUATION_DATE - dob).days + 1) / 365.25)
        assert expected == 35


class TestSalaryProjection:

    def test_year_zero_is_base_salary(self, engine):
        result = engine._calculate_employee(
            pd.Series({
                "emp_id": "1", "emp_name": "Test", "salary": 10000.0,
                "current_age": 59,  # one year only
            })
        )
        assert len(result) == 1
        assert result[0]["future_salary"] == pytest.approx(10000.0, rel=1e-5)

    def test_salary_compounds_correctly(self, engine):
        rows = engine._calculate_employee(
            pd.Series({
                "emp_id": "1", "emp_name": "Test", "salary": 10000.0,
                "current_age": 58,
            })
        )
        # Year 0: 10000, Year 1: 10000 * 1.05 = 10500
        assert rows[0]["future_salary"] == pytest.approx(10000.0, rel=1e-5)
        assert rows[1]["future_salary"] == pytest.approx(10500.0, rel=1e-5)


class TestOutflowFormula:

    def test_outflow_equals_salary_times_px_times_qx(self, engine):
        rows = engine._calculate_employee(
            pd.Series({
                "emp_id": "1", "emp_name": "Test", "salary": 10000.0,
                "current_age": 59,
            })
        )
        row = rows[0]
        expected = row["future_salary"] * row["px"] * row["qx"]
        assert row["expected_death_outflow"] == pytest.approx(expected, rel=1e-5)


class TestHappyPath:

    def test_run_produces_output_csv(self, engine):
        inp = _write_csv(VALID_CSV)
        out = _output_path()
        result = engine.run(input_path=inp, output_path=out)
        assert result["input_rows"] == 2
        assert result["output_rows"] > 0
        assert os.path.isfile(out)
        df = pd.read_csv(out)
        assert list(df.columns) == [
            "emp_id", "emp_name", "age", "future_salary", "px", "qx", "expected_death_outflow"
        ]
        os.unlink(inp)

    def test_all_employees_present_in_output(self, engine):
        inp = _write_csv(VALID_CSV)
        out = _output_path()
        engine.run(input_path=inp, output_path=out)
        df = pd.read_csv(out)
        assert set(df["emp_id"].astype(str)) == {"1", "2"}
        os.unlink(inp)


class TestInputValidation:

    def test_empty_csv_raises(self, engine):
        inp = _write_csv("")
        with pytest.raises(InputValidationError, match="empty"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_missing_column_raises(self, engine):
        inp = _write_csv("emp_id,emp_name,date_birth,date_joining\n1,Test,1990-01-01,2020-01-01\n")
        with pytest.raises(InputValidationError, match="Missing required columns"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_duplicate_emp_id_raises(self, engine):
        inp = _write_csv(
            "emp_id,emp_name,date_birth,date_joining,salary\n"
            "1,Emp A,1990-01-01,2020-01-01,5000\n"
            "1,Emp B,1991-01-01,2021-01-01,6000\n"
        )
        with pytest.raises(InputValidationError, match="Duplicate emp_id"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_invalid_date_raises(self, engine):
        inp = _write_csv(
            "emp_id,emp_name,date_birth,date_joining,salary\n"
            "1,Emp A,not-a-date,2020-01-01,5000\n"
        )
        with pytest.raises(InputValidationError, match="not a valid date"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_negative_salary_raises(self, engine):
        inp = _write_csv(
            "emp_id,emp_name,date_birth,date_joining,salary\n"
            "1,Emp A,1990-01-01,2020-01-01,-500\n"
        )
        with pytest.raises(InputValidationError, match="positive number"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_zero_salary_raises(self, engine):
        inp = _write_csv(
            "emp_id,emp_name,date_birth,date_joining,salary\n"
            "1,Emp A,1990-01-01,2020-01-01,0\n"
        )
        with pytest.raises(InputValidationError, match="positive number"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_dob_after_joining_raises(self, engine):
        inp = _write_csv(
            "emp_id,emp_name,date_birth,date_joining,salary\n"
            "1,Emp A,2022-01-01,2020-01-01,5000\n"
        )
        with pytest.raises(InputValidationError, match="date_birth >= date_joining"):
            engine.run(inp, _output_path())
        os.unlink(inp)

    def test_employee_past_retirement_produces_zero_rows(self, engine):
        # DOB making age >= 60 at valuation date 2024-12-31
        inp = _write_csv(
            "emp_id,emp_name,date_birth,date_joining,salary\n"
            "1,Old Emp,1960-01-01,1990-01-01,5000\n"
        )
        out = _output_path()
        result = engine.run(input_path=inp, output_path=out)
        assert result["output_rows"] == 0
        os.unlink(inp)

    def test_case_insensitive_column_headers(self, engine):
        inp = _write_csv(
            "EMP_ID,EMP_NAME,DATE_BIRTH,DATE_JOINING,SALARY\n"
            "1,Emp A,1990-01-01,2020-01-01,5000\n"
        )
        out = _output_path()
        result = engine.run(input_path=inp, output_path=out)
        assert result["input_rows"] == 1
        os.unlink(inp)
