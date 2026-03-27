from django.contrib import admin, messages as admin_messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils import timezone
from .models import Topic, Comment, Tag, TopicTag

# ==============================
# TopicTagインライン
# ==============================

class TopicTagInline(admin.TabularInline):
    model = TopicTag
    extra = 1
    autocomplete_fields = ("tag",)

# ==============================
# Topic
# ==============================

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "board_category", "status",
        "delete_request_status", "delete_request_reason", "user", "created_at"  
    )
    list_filter = ("board_category", "status", "delete_request_status")  
    search_fields = ("title", "text")
    inlines = [TopicTagInline]
    actions = ["approve_delete", "reject_delete"]  

    def approve_delete(self, request, queryset):
        count = queryset.filter(
            delete_request_status=Topic.DeleteRequestStatus.PENDING
        ).count()
        queryset.filter(
            delete_request_status=Topic.DeleteRequestStatus.PENDING
        ).delete()
        self.message_user(request, f"{count}件のトピックを削除しました。")
    approve_delete.short_description = "✅ 削除要請を承認して削除する"

    def reject_delete(self, request, queryset):
        queryset.update(
            delete_request_status=Topic.DeleteRequestStatus.REJECTED
        )
        self.message_user(request, "削除要請を却下しました。")
    reject_delete.short_description = "❌ 削除要請を却下する"
    

# ==============================
 	# Comment
# ==============================
 
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
    

# ==============================
# Tag
# ==============================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "merged_to_tag", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
    autocomplete_fields = ("merged_to_tag",)
    actions = ["go_to_move_page"]

    # ① アクション：確認ページへ飛ばす
    def go_to_move_page(self, request, queryset):
        selected_ids = ",".join(str(tag.id) for tag in queryset)
        return redirect(f"move-tags/?ids={selected_ids}")

    go_to_move_page.short_description = "選択したタグを別のタグに移動して削除する"

    # ② カスタムURLを登録
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "move-tags/",
                self.admin_site.admin_view(self.move_tags_view),
                name="tag_move",
            ),
        ]
        return custom + urls

    # ③ 確認ページのビュー
    def move_tags_view(self, request):
        ids_str = request.GET.get("ids", "") or request.POST.get("ids", "")
        ids = [int(i) for i in ids_str.split(",") if i.isdigit()]
        source_tags = Tag.objects.filter(id__in=ids)

        # --- ステップ１：移動先を選んで「確認へ」を押したとき ---
        if request.method == "POST" and request.POST.get("step") == "confirm":
            target_id = request.POST.get("target_tag")
            if not target_id:
                admin_messages.error(request, "移動先タグを選択してください。")
                # 選択画面に戻す（下のGETと同じ描画）
            else:
                target = Tag.objects.get(id=target_id)
                target_candidates = Tag.objects.filter(is_active=True).exclude(id__in=ids)
                # 確認画面を表示
                return render(request, "admin/board/tag_move.html", {
                    "step": "confirm",
                    "source_tags": source_tags,
                    "target": target,
                    "target_id": target_id,
                    "ids_str": ids_str,
                    "target_candidates": target_candidates,
                })

        # --- ステップ２：「はい、移動して削除」を押したとき ---
        if request.method == "POST" and request.POST.get("step") == "execute":
            target_id = request.POST.get("target_tag")
            target = Tag.objects.get(id=target_id)
            moved_names = []

            for tag in source_tags:
                if tag.id == target.id:
                    continue

                # TopicTag を付け替え
                for topic_tag in TopicTag.objects.filter(tag=tag):
                    already = TopicTag.objects.filter(
                        topic=topic_tag.topic, tag=target
                    ).exists()
                    if already:
                        topic_tag.delete()
                    else:
                        topic_tag.tag = target
                        topic_tag.save()

                moved_names.append(tag.name)
                tag.delete()  # 元タグを削除

            admin_messages.success(
                request,
                f"「{'」「'.join(moved_names)}」を「{target.name}」に移動して削除しました。",
            )
            return redirect("../")  # タグ一覧に戻る

        # --- GET：移動先を選ぶ画面 ---
        target_candidates = Tag.objects.filter(is_active=True).exclude(id__in=ids)
        return render(request, "admin/board/tag_move.html", {
            "step": "select",
            "source_tags": source_tags,
            "target_candidates": target_candidates,
            "ids_str": ids_str,
        })  


# ==============================
# TopicTag
# ==============================

@admin.register(TopicTag)
class TopicTagAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "tag", "created_at", "updated_at")
    search_fields = ("topic__title", "tag__name")
    autocomplete_fields = ("topic", "tag")