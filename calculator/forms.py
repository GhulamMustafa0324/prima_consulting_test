import os

from django import forms

from calculator.engine.constants import ALLOWED_UPLOAD_EXTENSION, MAX_UPLOAD_SIZE_BYTES


class UploadCSVForm(forms.Form):

    input_file = forms.FileField(
        label="Employee CSV File",
        help_text="Upload a CSV with columns: emp_id, emp_name, date_birth, date_joining, salary",
    )

    def clean_input_file(self):
        f = self.cleaned_data["input_file"]

        _, ext = os.path.splitext(f.name.lower())
        if ext != ALLOWED_UPLOAD_EXTENSION:
            raise forms.ValidationError(f"Only .csv files accepted. Got '{ext}'.")

        if f.size > MAX_UPLOAD_SIZE_BYTES:
            raise forms.ValidationError(
                f"File too large ({f.size / 1024 / 1024:.1f} MB). Limit is 5 MB."
            )
        return f
