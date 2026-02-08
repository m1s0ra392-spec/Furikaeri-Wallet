from django.urls import path
from . import views

app_name = "board"

urlpatterns = [
    path("", views.topic_list, name="topic_list"),#トピック一覧（掲示板トップ）
    path("new/", views.topic_create, name="topic_create"),#トピック作成
    path("topics/<int:topic_id>/", views.topic_detail, name="topic_detail"), #トピック詳細
    path("topics/<int:topic_id>/comments/new/", views.comment_create, name="comment_create"),#コメント作成
    path("topics/<int:topic_id>/like/", views.topic_like_toggle, name="topic_like_toggle"),#わたしのいいね（トピック）（仮）
    path("comments/<int:comment_id>/like/", views.comment_like_toggle, name="comment_like_toggle"),#わたしのいいね（コメント）（仮）
    path("api/tags/", views.tag_search_api, name="tag_search_api"),#タグ検索
]