from django.urls import path
from . import views

app_name = "board"

urlpatterns = [
    path("", views.topic_list, name="topic_list"),
]