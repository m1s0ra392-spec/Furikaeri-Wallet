from django.urls import path
from . import views

app_name = "board"

urlpatterns = [
    path("", views.topic_list, name="topic_list"),
    path("new/", views.topic_create, name="topic_create"),
]