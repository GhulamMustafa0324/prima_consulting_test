import logging
import os
import uuid

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from calculator.engine.calculator import CalculationEngine
from calculator.engine.exceptions import CalculationEngineError, InputValidationError
from calculator.forms import UploadCSVForm
from calculator.models import Execution

logger = logging.getLogger(__name__)


class UploadView(View):
    template_name = "calculator/upload.html"

    def get(self, request):
        return render(request, self.template_name, {"form": UploadCSVForm()})

    def post(self, request):
        form = UploadCSVForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        execution = Execution()
        # FileField.save() prepends upload_to="inputs/" automatically,
        # so pass only the filename here — not "inputs/<filename>".
        execution.input_file.save(
            f"{uuid.uuid4().hex}.csv",
            request.FILES["input_file"],
            save=False,
        )
        execution.save()
        return redirect("calculator:process", pk=execution.pk)


class ProcessView(View):
    template_name = "calculator/process_confirm.html"

    def get(self, request, pk: int):
        execution = get_object_or_404(Execution, pk=pk)
        if execution.status != Execution.Status.PENDING:
            return redirect("calculator:result", pk=pk)
        return render(request, self.template_name, {"execution": execution})

    def post(self, request, pk: int):
        execution = get_object_or_404(Execution, pk=pk)

        if execution.status != Execution.Status.PENDING:
            return redirect("calculator:result", pk=pk)

        input_path  = os.path.join(settings.MEDIA_ROOT, execution.input_file.name)
        output_rel  = f"outputs/{uuid.uuid4().hex}.csv"
        output_path = os.path.join(settings.MEDIA_ROOT, output_rel)

        try:
            result = CalculationEngine().run(input_path=input_path, output_path=output_path)
        except InputValidationError as exc:
            execution.mark_failed(str(exc))
        except CalculationEngineError as exc:
            logger.error("Engine error for Execution #%s", pk, exc_info=True)
            execution.mark_failed("A system error occurred during processing.")
        except Exception:
            logger.exception("Unexpected error for Execution #%s", pk)
            execution.mark_failed("An unexpected error occurred.")
        else:
            execution.mark_success(
                output_file_path=output_rel,
                input_rows=result["input_rows"],
                output_rows=result["output_rows"],
            )
        return redirect("calculator:result", pk=pk)


class ResultView(View):
    template_name = "calculator/result.html"

    def get(self, request, pk: int):
        execution = get_object_or_404(Execution, pk=pk)
        return render(request, self.template_name, {"execution": execution})


class HistoryView(ListView):
    model = Execution
    template_name = "calculator/history.html"
    context_object_name = "executions"
    paginate_by = 20


class DownloadView(View):

    def get(self, request, pk: int):
        execution = get_object_or_404(Execution, pk=pk)
        file_type = request.GET.get("file_type", "output")

        if file_type == "input":
            field = execution.input_file
        elif file_type == "output":
            field = execution.output_file
        else:
            raise Http404(f"Invalid file_type '{file_type}'.")

        if not field:
            raise Http404("File not available.")

        file_path = os.path.join(settings.MEDIA_ROOT, field.name)
        if not os.path.isfile(file_path):
            raise Http404("File not found on disk.")
        
        date_str = execution.created_at.strftime("%Y-%m-%d")
        download_name = f"{file_type}_{date_str}_exec{execution.pk}.csv"

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=download_name,
        )
