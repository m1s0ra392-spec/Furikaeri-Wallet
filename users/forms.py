from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True) 
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    
    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "このユーザー名はすでに使われています。別の名前を入力してください。"
            )
        return username


class UsernameChangeForm(forms.ModelForm):
    """ユーザーネーム変更フォーム"""
    class Meta:
        model = User
        fields = ['username']
        labels = {'username': '新しいユーザーネーム'}

    def clean_username(self):
        username = self.cleaned_data['username']
        # 自分以外で同じ名前がいたらエラー
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("このユーザーネームはすでに使われています。")
        return username


class EmailChangeForm(forms.Form):
    """メールアドレス変更フォーム"""
    email = forms.EmailField(label='新しいメールアドレス')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスはすでに使われています。")
        return email


class PasswordChangeForm(forms.Form):
    """パスワード変更フォーム（ログイン中）"""
    current_password = forms.CharField(
        label='現在のパスワード',
        widget=forms.PasswordInput
    )
    new_password1 = forms.CharField(
        label='新しいパスワード ※8文字以上・半角英数字で入力してください',
        widget=forms.PasswordInput
    )
    new_password2 = forms.CharField(
        label='パスワード再入力',
        widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        # userを受け取れるようにする（現在のPWチェックのため）
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        pw = self.cleaned_data['current_password']
        if not self.user.check_password(pw):
            raise forms.ValidationError("現在のパスワードが正しくありません。")
        return pw

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('new_password1')
        pw2 = cleaned.get('new_password2')
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("新しいパスワードが一致しません。")
        return cleaned