from django.contrib import admin

from calculator.models import Execution


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display  = ("pk", "status", "input_rows", "output_rows", "created_at", "processed_at")
    list_filter   = ("status",)
    readonly_fields = ("created_at", "processed_at", "input_rows", "output_rows", "error_message")
