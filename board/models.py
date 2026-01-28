from django.db import models
from django.conf import settings

class Topic(models.Model):
    class BoardCategory(models.IntegerChoices):
        OTOKU = 0, "お得情報"
        KUHUU = 1, "日々のひと工夫"
        MANABI = 2, "失敗からの学び"

    class Status(models.IntegerChoices):
        DRAFT = 0, "下書き"
        PUBLIC = 1, "公開"

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

    class Meta:
        db_table = "topics"  # 図のテーブル名に合わせる
        ordering = ["-created_at"]  # とりあえず新着順（人気順は後で）

    def __str__(self) -> str:
        return f"{self.title} ({self.get_board_category_display()})"