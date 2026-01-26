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