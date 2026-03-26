from django.urls import path
from django.contrib.auth import views as auth_views

from .import views


app_name = 'users'

urlpatterns = [
    path('signup/', views.signup, name='signup'),#アカウント登録

 # アカウントマイページ系
    #マイページ全体
    path('mypage/', views.account_mypage, name='account_mypage'),
    #ユーザーネーム変更
    path('mypage/username/', views.change_username, name='change_username'),
    #アドレス変更入力
    path('mypage/email/', views.change_email, name='change_email'),
    #アドレス変更（メール送信完了）
    path('mypage/email/sent/', views.change_email_sent, name='change_email_sent'),
    #アドレス変更完了（メールURLから）
    path('mypage/email/done/<uidb64>/<token>/', views.change_email_done, name='change_email_done'),
    #パスワード再設定（ログイン中）
    path('mypage/password/', views.change_password, name='change_password'),
    #カテゴリ追加編集
    path('categories/', views.category_list, name='category_list'),#一覧
    path('categories/add/', views.category_add, name='category_add'),#追加
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),#編集
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),#削除
    #アカウントリセット
    path('account-reset/', views.account_reset_confirm, name='account_reset_confirm'),#リセット確認
    path('account-reset/execute/', views.account_reset_execute, name='account_reset_execute'),#リセット実行
    #ログアウトしました
    path('logout-done/', views.logout_done, name='logout_done'),
 
]