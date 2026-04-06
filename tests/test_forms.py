import io

import django
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from calculator.forms import UploadCSVForm
from calculator.engine.constants import MAX_UPLOAD_SIZE_BYTES


class TestUploadCSVForm(TestCase):

    def _make_file(self, name: str, content: bytes = b"emp_id,emp_name\n1,Test\n") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content, content_type="text/csv")

    def test_valid_csv_passes(self):
        f = self._make_file("employees.csv")
        form = UploadCSVForm(files={"input_file": f})
        assert form.is_valid(), form.errors

    def test_wrong_extension_rejected(self):
        f = self._make_file("employees.xlsx")
        form = UploadCSVForm(files={"input_file": f})
        assert not form.is_valid()
        assert "Only .csv files accepted" in str(form.errors)

    def test_txt_extension_rejected(self):
        f = self._make_file("employees.txt")
        form = UploadCSVForm(files={"input_file": f})
        assert not form.is_valid()

    def test_oversized_file_rejected(self):
        big_content = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)
        f = self._make_file("big.csv", big_content)
        form = UploadCSVForm(files={"input_file": f})
        assert not form.is_valid()
        assert "too large" in str(form.errors)

    def test_no_file_invalid(self):
        form = UploadCSVForm(files={})
        assert not form.is_valid()
