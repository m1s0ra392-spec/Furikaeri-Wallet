
from django.contrib.auth import update_session_auth_hash, logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.conf import settings
from .forms import SignUpForm, UsernameChangeForm, EmailChangeForm, PasswordChangeForm, CustomSetPasswordForm
from .models import User
from django.shortcuts import render, redirect, get_object_or_404
from records.models import Record, RecordCategory

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

            login(request, user)
            return redirect('records:home')
    else:
        form = SignUpForm()
    
    return render(request, 'users/signup.html', {'form': form})
        

class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'registration/password_reset_confirm.html'

        
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
    # "?reset=done" が付いていたら完了モーダルを出す
    reset_done = request.GET.get("reset") == "done"
    return render(request, 'users/mypage.html', {
        'changed': changed,
        'reset_done': reset_done,
    })    


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


#アカウントリセット

# デフォルトカテゴリの定義
DEFAULT_CATEGORIES = [
    {"name": "クーポン・割引", "type": 0},
    {"name": "チラシ",         "type": 0},
    {"name": "我慢した",       "type": 0},
    {"name": "捨てずに譲った", "type": 0},
    {"name": "その他",         "type": 0},
    {"name": "衝動買い",       "type": 1},
    {"name": "時間がなかった", "type": 1},
    {"name": "その他",         "type": 1},
]

@login_required
def account_reset_execute(request):
    if request.method == "POST":
        user = request.user

        # 記録を全削除
        Record.objects.filter(user=user).delete()

        # カテゴリを全削除（ユーザー定義・デフォルト両方）
        RecordCategory.objects.filter(user=user).delete()

        # デフォルトカテゴリを再投入
        for cat in DEFAULT_CATEGORIES:
            RecordCategory.objects.create(
                user=user,
                name=cat["name"],
                type=cat["type"],
                system_default=1,
            )

        return redirect("/users/mypage/?reset=done")

    return redirect("users:account_reset_confirm")



def logout_done(request):
    """ログアウト完了画面（GETでアクセス）"""
    logout(request)  # ここでログアウト実行
    return render(request, 'users/logout_done.html')


# ==============================
# カテゴリ管理
# ==============================

@login_required
def category_list(request):
    success = request.GET.get("success")

    def sort_categories(qs):
        others = [c for c in qs if c.name == "その他"]
        rest = [c for c in qs if c.name != "その他"]
        return rest + others  # 「その他」を末尾に

    gain_qs = RecordCategory.objects.filter(user=request.user, type=0).order_by("created_at")
    loss_qs = RecordCategory.objects.filter(user=request.user, type=1).order_by("created_at")

    return render(request, "users/category_list.html", {
        "gain_categories": sort_categories(gain_qs),
        "loss_categories": sort_categories(loss_qs),
        "success": success,
    })

@login_required
def category_add(request):
    """カテゴリ追加"""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        type_ = request.POST.get("type")
        tab = "loss" if type_ == "1" else "gain"

        # ── バリデーション ──
        if not name:
            return redirect(f"/users/categories/?error=empty&tab={tab}")

        if type_ in ("0", "1"):
            exists = RecordCategory.objects.filter(
                user=request.user, name=name, type=int(type_)
            ).exists()
            if exists:
                return redirect(f"/users/categories/?error=duplicate&tab={tab}")

            RecordCategory.objects.create(
                user=request.user,
                name=name,
                type=int(type_),
                system_default=0,
            )

        return redirect(f"/users/categories/?success=added&tab={tab}")
    return render(request, "users/category_form.html", {"mode": "add"})

@login_required
def category_edit(request, pk):
    """カテゴリ編集"""
    category = get_object_or_404(RecordCategory, pk=pk, user=request.user)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            category.name = name
            category.save()
        return redirect("/users/categories/?success=edited")
    return render(request, "users/category_form.html", {"mode": "edit", "category": category})


@login_required
def category_delete(request, pk):
    """カテゴリ削除"""
    category = get_object_or_404(RecordCategory, pk=pk, user=request.user)
    if request.method == "POST":
        # 「その他」カテゴリを取得（同じtype・同じユーザー・system_default=1）
        fallback = RecordCategory.objects.filter(
            user=request.user,
            type=category.type,
            system_default=1,
            name="その他"
        ).first()
        
        if fallback:
            # このカテゴリに紐づく記録を「その他」に付け替える
            Record.objects.filter(user=request.user, category=category).update(category=fallback)
        
        category.delete()
        return redirect("/users/categories/?success=deleted")
    return redirect("users:category_list")

@login_required
def category_bulk_delete(request):
    """チェックされた複数カテゴリを一括削除"""
    if request.method == "POST":
        pks = request.POST.getlist("pks")  # チェックされたpkのリスト
        if pks:
            for pk in pks:
                category = RecordCategory.objects.filter(
                    pk=pk, user=request.user, system_default=0
                ).first()
                if category:
                    # 「その他」に記録を移動
                    fallback = RecordCategory.objects.filter(
                        user=request.user,
                        type=category.type,
                        name="その他"
                    ).first()
                    if fallback:
                        Record.objects.filter(
                            user=request.user, category=category
                        ).update(category=fallback)
                    category.delete()

        return redirect("/users/categories/?success=deleted")
    return redirect("users:category_list")