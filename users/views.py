
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.conf import settings
from .forms import SignUpForm, UsernameChangeForm, EmailChangeForm, PasswordChangeForm
from .models import User
from django.shortcuts import render, redirect
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


    
# ==============================
# アカウントマイページ
# ==============================

@login_required
def account_mypage(request):
    # 変更完了メッセージ（ユーザーネーム・パスワード変更後）
    changed = request.GET.get('changed')  # 'username' or 'password'
    return render(request, 'users/mypage.html', {'changed': changed})


""""ユーザーネーム変更"""
@login_required
def change_username(request):
    if request.method == 'POST':
        form = UsernameChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            # マイページに戻る（完了メッセージ付き）
            return redirect(reverse('users:account_mypage') + '?changed=username')
    else:
        form = UsernameChangeForm(instance=request.user)
    return render(request, 'users/mypage_username.html', {'form': form})


"""メールアドレス変更"""
@login_required
def change_email(request):
    if request.method == 'POST':
        form = EmailChangeForm(request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['email']
            # 新メールアドレスをセッションに一時保存（まだDBには書かない）
            request.session['new_email'] = new_email

            # 確認メールを送る
            uid = urlsafe_base64_encode(force_bytes(request.user.pk))
            token = default_token_generator.make_token(request.user)
            confirm_url = request.build_absolute_uri(
                f"/users/mypage/email/done/{uid}/{token}/"
            )
            send_mail(
                subject='【ふりかえり財布】メールアドレス変更の確認',
                message=f'以下のURLをクリックするとメールアドレスが変更されます。\n\n{confirm_url}\n\nURLの有効期限は10分です。',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[new_email],
            )
            return redirect('users:change_email_sent')
    else:
        form = EmailChangeForm()
    return render(request, 'users/mypage_email.html', {'form': form})


@login_required
def change_email_sent(request):
    """メール送信完了画面"""
    return render(request, 'users/mypage_email_sent.html')


def change_email_done(request, uidb64, token):
    """メール内URLをクリックしたときの処理"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user and default_token_generator.check_token(user, token):
        new_email = request.session.get('new_email')
        if new_email:
            user.email = new_email
            user.save()
            del request.session['new_email']
        return render(request, 'users/mypage_email_done.html')
    else:
        # トークン無効（期限切れなど）
        return render(request, 'users/mypage_email_done.html', {'error': True})


"""パスワード変更（ログイン中）"""
@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.save()
            # パスワード変更後もログアウトしないようにする
            update_session_auth_hash(request, request.user)
            return redirect(reverse('users:account_mypage') + '?changed=password')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/mypage_password.html', {'form': form})


"""アカウントリセット"""
@login_required
def account_reset(request):
    # TODO: 後で実装
    return redirect('users:account_mypage')

def logout_done(request):
    """ログアウト完了画面（GETでアクセス）"""
    logout(request)  # ここでログアウト実行
    return render(request, 'users/logout_done.html')