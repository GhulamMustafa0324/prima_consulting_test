from django.urls import path

from calculator import views

app_name = "calculator"

urlpatterns = [
    path("",                   views.UploadView.as_view(),  name="upload"),
    path("process/<int:pk>/",  views.ProcessView.as_view(), name="process"),
    path("result/<int:pk>/",   views.ResultView.as_view(),  name="result"),
    path("history/",           views.HistoryView.as_view(), name="history"),
    path("download/<int:pk>/", views.DownloadView.as_view(), name="download"),
]
