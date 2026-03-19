from django.shortcuts import render, redirect
from .forms import SignUpForm
from records.models import RecordCategory

from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm


# ==============================
# 新規登録
# ==============================

def signup(request):   
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # ← 戻り値を user に受け取るよう変更

            # ★新規登録時にデフォルトカテゴリを自動作成
            default_categories = [
                # (name, type, system_default)
                ("クーポン・割引", 0, 0),
                ("チラシ",         0, 0),
                ("我慢した",       0, 0),
                ("捨てずに譲った", 0, 0),
                ("その他",         0, 1),  # system_default=1：削除不可
                ("衝動買い",       1, 0),
                ("時間がなかった", 1, 0),
                ("その他",         1, 1),  # system_default=1：削除不可
            ]
            for name, type_, system_default in default_categories:
                RecordCategory.objects.create(
                    user=user,
                    name=name,
                    type=type_,
                    system_default=system_default,
                )

            return redirect('login')
    else:
        form = SignUpForm()
    
    return render(request, 'users/signup.html', {'form': form})
        
        
class PasswordResetCompleteToLoginView(auth_views.PasswordResetCompleteView):
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ログインフォームを表示するために明示的に渡す
        context["form"] = AuthenticationForm(self.request)
        # 「再設定できました」メッセージ表示用フラグ
        context["password_reset_completed"] = True
        return context