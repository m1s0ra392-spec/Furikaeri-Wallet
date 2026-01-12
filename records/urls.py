from django.urls import path
from . import views

app_name = "records"

urlpatterns = [
    path("new/", views.record_create, name="record_create"),
]