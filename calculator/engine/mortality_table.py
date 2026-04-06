import os

import pandas as pd

from calculator.engine.exceptions import MortalityTableLoadError, MortalityTableLookupError

_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "mortality_table.csv")


class MortalityTable:
    """Loads and provides O(1) lookups against the mortality probability table."""

    def __init__(self, filepath: str = _DATA_FILE) -> None:
        self._table: dict[int, dict[str, float]] = {}
        self._load(filepath)

    def _load(self, filepath: str) -> None:
        try:
            df = pd.read_csv(filepath)
        except FileNotFoundError:
            raise MortalityTableLoadError(f"Mortality table not found: {filepath}")
        except Exception as exc:
            raise MortalityTableLoadError(f"Could not load mortality table: {exc}") from exc

        required = {"age", "qx", "px"}
        if not required.issubset(df.columns):
            raise MortalityTableLoadError(
                f"Mortality table missing columns. Expected {required}, got {set(df.columns)}."
            )

        if df.empty:
            raise MortalityTableLoadError("Mortality table is empty.")

        invalid = df[(df["qx"] < 0) | (df["qx"] > 1) | (df["px"] < 0) | (df["px"] > 1)]
        if not invalid.empty:
            raise MortalityTableLoadError(
                f"Invalid probabilities at ages: {invalid['age'].tolist()}. Must be in [0, 1]."
            )

        self._table = {
            int(row["age"]): {"qx": float(row["qx"]), "px": float(row["px"])}
            for _, row in df.iterrows()
        }

    def lookup(self, age: int) -> dict[str, float]:
        if age not in self._table:
            raise MortalityTableLookupError(
                f"Age {age} not in mortality table (range: {min(self._table)}–{max(self._table)})."
            )
        return self._table[age]
