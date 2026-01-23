from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("id", "email", "username", "is_staff", "is_active", "date_joined")
    ordering = ("id",)
    search_fields = ("email", "username")