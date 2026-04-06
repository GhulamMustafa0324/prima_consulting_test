import os
import tempfile

import pandas as pd
import pytest

from calculator.engine.exceptions import MortalityTableLoadError, MortalityTableLookupError
from calculator.engine.mortality_table import MortalityTable


def _write_csv(data: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    f.write(data)
    f.close()
    return f.name


class TestMortalityTableLoad:

    def test_loads_successfully(self):
        path = _write_csv("age,qx,px\n35,0.002289,0.997711\n40,0.003211,0.996789\n")
        table = MortalityTable(filepath=path)
        assert len(table._table) == 2
        os.unlink(path)

    def test_missing_file_raises(self):
        with pytest.raises(MortalityTableLoadError, match="not found"):
            MortalityTable(filepath="/nonexistent/path.csv")

    def test_missing_column_raises(self):
        path = _write_csv("age,qx\n35,0.002\n")
        with pytest.raises(MortalityTableLoadError, match="missing columns"):
            MortalityTable(filepath=path)
        os.unlink(path)

    def test_empty_file_raises(self):
        path = _write_csv("age,qx,px\n")
        with pytest.raises(MortalityTableLoadError, match="empty"):
            MortalityTable(filepath=path)
        os.unlink(path)

    def test_invalid_probability_raises(self):
        path = _write_csv("age,qx,px\n35,1.5,0.997711\n")
        with pytest.raises(MortalityTableLoadError, match="Invalid probabilities"):
            MortalityTable(filepath=path)
        os.unlink(path)


class TestMortalityTableLookup:

    def setup_method(self):
        path = _write_csv("age,qx,px\n35,0.002289,0.997711\n40,0.003211,0.996789\n")
        self.table = MortalityTable(filepath=path)
        os.unlink(path)

    def test_lookup_returns_correct_values(self):
        result = self.table.lookup(35)
        assert result["qx"] == pytest.approx(0.002289)
        assert result["px"] == pytest.approx(0.997711)

    def test_lookup_missing_age_raises(self):
        with pytest.raises(MortalityTableLookupError, match="not in mortality table"):
            self.table.lookup(99)
