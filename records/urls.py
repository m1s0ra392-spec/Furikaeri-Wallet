from django.urls import path
from . import views

app_name = "records"

urlpatterns = [
    path("new/", views.record_create, name="record_create"), #記録入力画面
    path("", views.record_list, name="record_list"), #記録一覧（カレンダーの上から）
    path("<int:pk>/edit/", views.record_update, name="record_update"),#記録編集
    path("<int:pk>/delete/", views.record_delete, name="record_delete"),#記録削除
]