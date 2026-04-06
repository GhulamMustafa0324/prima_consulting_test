import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from calculator.models import Execution

VALID_CSV_CONTENT = (
    b"emp_id,emp_name,date_birth,date_joining,salary\n"
    b"1,Employee 1,1989-02-07,2024-02-07,11280.25\n"
    b"2,Employee 2,2001-04-08,2024-06-02,8029.80\n"
)

INVALID_CSV_CONTENT = (
    b"emp_id,emp_name,date_birth,date_joining,salary\n"
    b"1,Employee 1,not-a-date,2024-02-07,11280.25\n"
)


def _upload_file(name: str = "test.csv", content: bytes = VALID_CSV_CONTENT) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="text/csv")


class TestUploadView(TestCase):

    def test_get_renders_form(self):
        response = self.client.get(reverse("calculator:upload"))
        assert response.status_code == 200
        assert b"Upload" in response.content

    def test_valid_post_creates_execution_and_redirects(self):
        response = self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file()},
        )
        assert response.status_code == 302
        assert Execution.objects.count() == 1
        ex = Execution.objects.first()
        assert ex.status == Execution.Status.PENDING
        assert response["Location"] == reverse("calculator:process", kwargs={"pk": ex.pk})

    def test_wrong_extension_returns_form_with_error(self):
        response = self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file("data.xlsx")},
        )
        assert response.status_code == 200
        assert Execution.objects.count() == 0
        assert b"Only .csv" in response.content


class TestProcessView(TestCase):

    def _create_pending(self) -> Execution:
        self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file()},
        )
        return Execution.objects.first()

    def test_get_shows_confirm_page(self):
        ex = self._create_pending()
        response = self.client.get(reverse("calculator:process", kwargs={"pk": ex.pk}))
        assert response.status_code == 200
        assert b"Run Calculation" in response.content

    def test_post_runs_engine_and_redirects_to_result(self):
        ex = self._create_pending()
        response = self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        assert response.status_code == 302
        ex.refresh_from_db()
        assert ex.status == Execution.Status.SUCCESS
        assert ex.input_rows == 2
        assert ex.output_rows > 0

    def test_invalid_csv_marks_failed(self):
        self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file(content=INVALID_CSV_CONTENT)},
        )
        ex = Execution.objects.first()
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        ex.refresh_from_db()
        assert ex.status == Execution.Status.FAILED
        assert ex.error_message != ""

    def test_double_post_is_idempotent(self):
        ex = self._create_pending()
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        ex.refresh_from_db()
        first_status = ex.status
        # Second POST should not re-run
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        ex.refresh_from_db()
        assert ex.status == first_status

    def test_get_already_processed_redirects_to_result(self):
        ex = self._create_pending()
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        response = self.client.get(reverse("calculator:process", kwargs={"pk": ex.pk}))
        assert response.status_code == 302
        assert "result" in response["Location"]


class TestResultView(TestCase):

    def _run_execution(self, content: bytes = VALID_CSV_CONTENT) -> Execution:
        self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file(content=content)},
        )
        ex = Execution.objects.first()
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        ex.refresh_from_db()
        return ex

    def test_result_shows_success_summary(self):
        ex = self._run_execution()
        response = self.client.get(reverse("calculator:result", kwargs={"pk": ex.pk}))
        assert response.status_code == 200
        assert b"Success" in response.content
        assert str(ex.input_rows).encode() in response.content
        assert str(ex.output_rows).encode() in response.content

    def test_result_shows_error_for_failed(self):
        ex = self._run_execution(content=INVALID_CSV_CONTENT)
        response = self.client.get(reverse("calculator:result", kwargs={"pk": ex.pk}))
        assert response.status_code == 200
        assert b"Failed" in response.content
        assert b"not a valid date" in response.content


class TestHistoryView(TestCase):

    def test_empty_history(self):
        response = self.client.get(reverse("calculator:history"))
        assert response.status_code == 200
        assert b"No executions yet" in response.content

    def test_history_lists_executions(self):
        self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file()},
        )
        response = self.client.get(reverse("calculator:history"))
        assert response.status_code == 200
        assert b"Pending" in response.content


class TestDownloadView(TestCase):

    def _run_success(self) -> Execution:
        self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file()},
        )
        ex = Execution.objects.first()
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        ex.refresh_from_db()
        return ex

    def test_download_output_csv(self):
        ex = self._run_success()
        response = self.client.get(
            reverse("calculator:download", kwargs={"pk": ex.pk}),
            {"file_type": "output"},
        )
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment")

    def test_download_input_csv(self):
        ex = self._run_success()
        response = self.client.get(
            reverse("calculator:download", kwargs={"pk": ex.pk}),
            {"file_type": "input"},
        )
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment")

    def test_invalid_file_type_returns_404(self):
        ex = self._run_success()
        response = self.client.get(
            reverse("calculator:download", kwargs={"pk": ex.pk}),
            {"file_type": "garbage"},
        )
        assert response.status_code == 404

    def test_output_not_available_on_failed_returns_404(self):
        self.client.post(
            reverse("calculator:upload"),
            {"input_file": _upload_file(content=INVALID_CSV_CONTENT)},
        )
        ex = Execution.objects.first()
        self.client.post(reverse("calculator:process", kwargs={"pk": ex.pk}))
        ex.refresh_from_db()
        response = self.client.get(
            reverse("calculator:download", kwargs={"pk": ex.pk}),
            {"file_type": "output"},
        )
        assert response.status_code == 404
