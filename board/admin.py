from django.contrib import admin
from .models import Topic
from .models import Comment
# Register your models here.

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "board_category", "status", "user", "created_at")
    list_filter = ("board_category", "status")
    search_fields = ("title", "text")
    
admin.site.register(Comment)