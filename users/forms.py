from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True) #いるのかな、この１行あとで消すかも
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        