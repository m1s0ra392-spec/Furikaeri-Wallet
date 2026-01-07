from django.shortcuts import render, redirect
from .forms import SignUpForm

from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm


def signup(request):   #新規登録
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignUpForm()
    
    return render(request, 'users/signup.html', {'form':form})
        
        
class PasswordResetCompleteToLoginView(auth_views.PasswordResetCompleteView):
    template_name = "users/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ログインフォームを表示するために明示的に渡す
        context["form"] = AuthenticationForm(self.request)
        # 「再設定できました」メッセージ表示用フラグ
        context["password_reset_completed"] = True
        return context