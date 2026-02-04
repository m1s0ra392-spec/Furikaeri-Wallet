from django.db import models
from django.conf import settings


# ==============================
# topicsテーブル
# ==============================

class Topic(models.Model):
    class BoardCategory(models.IntegerChoices):
        OTOKU = 0, "お得情報"
        KUHUU = 1, "日々のひと工夫"
        MANABI = 2, "失敗からの学び"

    class Status(models.IntegerChoices):
        DRAFT = 0, "下書き"
        PUBLIC = 1, "公開"
        
    # 削除要請ステータス
    class DeleteRequestStatus(models.IntegerChoices):
        NONE = 0, "未申請"
        PENDING = 1, "申請中"
        APPROVED = 2, "承認"
        REJECTED = 3, "却下"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    board_category = models.IntegerField(choices=BoardCategory.choices)
    title = models.CharField(max_length=50)
    text = models.CharField(max_length=1000)
    status = models.IntegerField(choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# 削除要請情報（ユーザー入力必須は View/Form 側で担保）
    delete_request_status = models.IntegerField(
        choices=DeleteRequestStatus.choices,
        default=DeleteRequestStatus.NONE,
    )
    delete_request_reason = models.CharField(
        max_length=300,
        blank=True,   # 未申請のときは空でOK
    )
    delete_requested_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "topics"  
        ordering = ["-created_at"]  # とりあえず新着順（人気順は後で）

    def __str__(self) -> str:
        return f"{self.title} ({self.get_board_category_display()})"
  
    
# ==============================
# commentsテーブル
# ==============================

class Comment(models.Model):
    class Status(models.IntegerChoices):
        DRAFT = 0, "下書き"
        PUBLIC = 1, "公開"

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="board_comments",
    )
    text = models.CharField(max_length=1000)

    sequence = models.PositiveIntegerField()  # トピック内のコメントの通し番号
    

    # 返信（親コメント）。NULL許容＝親なし（通常コメント）
    parent_comment = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )

    status = models.IntegerField(choices=Status.choices, default=Status.PUBLIC)
    
    # 論理削除（表示だけ「削除されました」にする）
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_board_comments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "sequence"],
                name="uq_comment_sequence_per_topic",
        )
    ]

    def __str__(self):
        return f"#{self.sequence} {self.text[:20]}"
    
    
    
# ==============================
# topic_likesテーブル
# ==============================

class TopicLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_likes",
    )
    topic = models.ForeignKey(
        "board.Topic",  # 同ファイル内なら "Topic" でもOK
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(                #同じユーザーが同じ対象に複数いいねできない
                fields=["user", "topic"],
                name="unique_user_topic_like",
            )
        ]

    def __str__(self):
        return f"TopicLike(user={self.user_id}, topic={self.topic_id})"
    
    
# ==============================
# comment_likesテーブル
# ==============================

class CommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_likes",
    )
    comment = models.ForeignKey(
        "board.Comment",
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(                   #同じユーザーが同じ対象に複数いいねできない
                fields=["user", "comment"],
                name="unique_user_comment_like",     
            )
        ]

    def __str__(self):
        return f"CommentLike(user={self.user_id}, comment={self.comment_id})"