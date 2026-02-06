from django.contrib import admin
from .models import Topic, Comment, Tag, TopicTag

# Register your models here.

class TopicTagInline(admin.TabularInline):
    model = TopicTag
    extra = 1
    autocomplete_fields = ("tag",)

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "board_category", "status", "user", "created_at")
    list_filter = ("board_category", "status")
    search_fields = ("title", "text")
    inlines = [TopicTagInline]
    
admin.site.register(Comment)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "merged_to_tag", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
    autocomplete_fields = ("merged_to_tag",)


@admin.register(TopicTag)
class TopicTagAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "tag", "created_at", "updated_at")
    search_fields = ("topic__title", "tag__name")
    autocomplete_fields = ("topic", "tag")