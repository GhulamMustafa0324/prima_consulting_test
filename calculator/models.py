from django.db import models
from django.utils import timezone


class Execution(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED  = "failed",  "Failed"

    input_file    = models.FileField(upload_to="inputs/")
    output_file   = models.FileField(upload_to="outputs/", null=True, blank=True)
    status        = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    input_rows    = models.IntegerField(null=True, blank=True)
    output_rows   = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at    = models.DateTimeField(auto_now_add=True)
    processed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Execution #{self.pk} — {self.status} — {self.created_at:%Y-%m-%d %H:%M}"

    def mark_success(self, output_file_path: str, input_rows: int, output_rows: int) -> None:
        self.output_file  = output_file_path
        self.status       = self.Status.SUCCESS
        self.input_rows   = input_rows
        self.output_rows  = output_rows
        self.processed_at = timezone.now()
        self.save()

    def mark_failed(self, error_message: str) -> None:
        self.status        = self.Status.FAILED
        self.error_message = error_message
        self.processed_at  = timezone.now()
        self.save()
