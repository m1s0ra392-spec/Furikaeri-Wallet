
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users.views import PasswordResetCompleteToLoginView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  
    # Django標準の認証URL（password_resetなど一式）
    
    # ★ 完了画面は login.html を再利用して赤字表示
    path(
        "accounts/password_reset/complete/",
        PasswordResetCompleteToLoginView.as_view(),
        name="password_reset_complete",
    ),

    
    path("users/", include("users.urls")),
    path("records/", include(("records.urls", "records"), namespace="records")),
    path("board/", include("board.urls")),
]