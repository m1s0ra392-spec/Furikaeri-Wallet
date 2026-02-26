from django.urls import path
from . import views

app_name = "board"

urlpatterns = [
    #掲示板トップ～閲覧・検索
    path("", views.topic_list, name="topic_list"),#トピック一覧（掲示板トップ）
    path("topics/<int:pk>/", views.topic_detail, name="topic_detail"), #トピック詳細
    
    
    #トピック
    path("new/", views.topic_create, name="topic_create"),#トピック作成
      #path("topics/<int:pk>/confirm/", views.topic_confirm, name="topic_confirm"),#トピック確認
    path("topics/confirm/", views.topic_confirm, name="topic_confirm"),#トピック確認
    path("topics/<int:pk>/edit/", views.topic_edit, name="topic_edit"),  # トピック編集（公開済み）
    path("drafts/<int:pk>/edit/", views.draft_topic_edit, name="draft_topic_edit"),#トピック編集（下書き）
    path("topics/<int:pk>/delete-request/", views.topic_delete_request, name="topic_delete_request"),#トピック削除リクエスト
    
    
    #コメント
    path("topics/<int:pk>/comments/new/", views.comment_create, name="comment_create"),#コメント作成
    path("comments/<int:pk>/edit/", views.comment_edit, name="comment_edit"),# コメント（公開・下書き共通で編集画面）
    path("comments/<int:pk>/confirm/", views.comment_confirm, name="comment_confirm"),# コメント編集の確認（編集→confirm）
    
    path("topics/<int:pk>/like/", views.topic_like_toggle, name="topic_like_toggle"),#トピックのいいね
    path("comments/<int:pk>/like/", views.comment_like_toggle, name="comment_like_toggle"),#コメントのいいね
    
    path("api/tags/", views.tag_search_api, name="tag_search_api"),#タグ検索
    
    
    #掲示板マイページ
    path("mypage/", views.mypage_index, name="mypage_index"),#掲示板マイページ

    path("mypage/likes/", views.mypage_likes, name="mypage_likes"),#私のいいね
    path("mypage/topics/", views.mypage_topics, name="mypage_topics"),#私のトピック
    path("mypage/comments/", views.mypage_comments, name="mypage_comments"),#私のコメント
    path("mypage/drafts/", views.mypage_drafts, name="mypage_drafts"),#下書き一覧
    
]
