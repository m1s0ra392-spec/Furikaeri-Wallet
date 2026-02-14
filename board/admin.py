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
    
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "topic_title",
        "sequence",
        "reply_to",
        "short_text",
        "status",
        "user",
        "created_at",
        "is_deleted",
    )

    list_select_related = ("topic", "user", "parent_comment")

    list_filter = ("status", "is_deleted", "created_at")

    search_fields = ("text", "topic__title", "user__username")

    ordering = ("-created_at",)

    # ===== カスタム表示 =====

    def topic_title(self, obj):
        return obj.topic.title
    topic_title.short_description = "Topic"

    def reply_to(self, obj):
        if obj.parent_comment:
            return f"#{obj.parent_comment.sequence}"
        return "-"
    reply_to.short_description = "Reply To"

    def short_text(self, obj):
        return obj.text[:20]
    short_text.short_description = "Comment"
    

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