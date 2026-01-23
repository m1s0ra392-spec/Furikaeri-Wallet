from django.contrib import admin
from .models import RecordCategory, Record


@admin.register(RecordCategory)
class RecordCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "system_default", "user")
    list_filter = ("type", "system_default")
    search_fields = ("name", "user__email", "user__username")
    ordering = ("id",)


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "amount", "date", "created_at")
    list_filter = ("date", "category__type")
    search_fields = ("memo", "category__name", "user__email", "user__username")
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")