import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        if len(username) < 4:
            raise forms.ValidationError("ユーザーネームは4文字以上で設定してください")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("このユーザーネームはすでに使われています")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        # 全角文字チェック（全角英数字・全角@など）
        if re.search(r'[^\x00-\x7F]', email):
            raise forms.ValidationError("メールアドレスの形式が正しくありません")
        # @の有無チェック（EmailFieldが通過させた場合の念のための確認）
        if "@" not in email:
            raise forms.ValidationError("メールアドレスの形式が正しくありません")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスはすでに使われています")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1", "")
        if len(password) < 8:
            raise forms.ValidationError("パスワードは8文字以上にしてください")
        if not re.search(r'[a-zA-Z]', password):
            raise forms.ValidationError("パスワードは英字と数字を両方含めてください")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("パスワードは英字と数字を両方含めてください")
        if not re.match(r'^[a-zA-Z0-9]+$', password):
            raise forms.ValidationError("パスワードは英数字の組み合わせにしてください")
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data.get("password2", "")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("パスワードが一致しません")
        return password2
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.pop("size", None)
            
        self.fields['username'].widget.attrs['placeholder'] = '4文字以上で入力してください'
        self.fields['email'].widget.attrs['placeholder'] = 'example@email.com'
        self.fields['password1'].widget.attrs['placeholder'] = '半角英数字を含む8文字以上'
        self.fields['password2'].widget.attrs['placeholder'] = 'パスワードを再入力してください'



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

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1", "")
        if len(password) < 8:
            raise forms.ValidationError("パスワードは8文字以上にしてください")
        if not re.search(r'[a-zA-Z]', password):
            raise forms.ValidationError("パスワードは英字と数字を両方含めてください")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("パスワードは英字と数字を両方含めてください")
        if not re.match(r'^[a-zA-Z0-9]+$', password):
            raise forms.ValidationError("パスワードは英数字の組み合わせにしてください")
        return password

    def clean_new_password2(self):
        pw1 = self.cleaned_data.get('new_password1')
        pw2 = self.cleaned_data.get('new_password2', '')
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("新しいパスワードが一致しません")
        return pw2