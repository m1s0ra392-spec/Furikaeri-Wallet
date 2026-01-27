from django.contrib import admin
from .models import RecordCategory, Record
from .models import AdviceMessage



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
    
    
@admin.register(AdviceMessage)
class AdviceMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "threshold_min", "threshold_max", "needs_calculation", "max_reward_amount", "updated_at")
    list_filter = ("needs_calculation",)
    search_fields = ("message_content",)
