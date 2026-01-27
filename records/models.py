from django.db import models
from users.models import User
from django.conf import settings #ユーザーモデルとの紐づけで利用（現在未使用）
from django.db import models


# ==============================
# ER図　record_categories
# ==============================

class RecordCategory(models.Model):
    TYPE_CHOICES = (
        (0, 'うまくいった'),
        (1, '惜しかった'),
    )

    SYSTEM_DEFAULT_CHOICES = (
        (0, 'ユーザー定義'),  #その他以外のカテゴリ
        (1, 'システム固定'),  #その他（削除不可）
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='record_categories'
    )
    name = models.CharField(max_length=20)
    type = models.IntegerField(choices=TYPE_CHOICES)
    system_default = models.IntegerField(
        choices=SYSTEM_DEFAULT_CHOICES,
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name




# ==============================
# ER図　records
# ==============================

class Record(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='records'
    )
    category = models.ForeignKey(
        RecordCategory,
        on_delete=models.PROTECT,
        related_name='records'
    )
    date = models.DateField()
    amount = models.IntegerField()
    memo = models.TextField(max_length=200, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} {self.category.name} {self.amount}"
    
    
# ==============================
# ER図　advice_messages
# ==============================

class AdviceMessage(models.Model):
    threshold_min = models.IntegerField()
    threshold_max = models.IntegerField(null=True, blank=True)  # NULLなら上限なし
    message_content = models.TextField()

    # 0:そのまま表示 / 1:計算(例: 30%ルール)を適用
    needs_calculation = models.BooleanField(default=False)

    # 還元提案の上限（needs_calculation=True の時に使う）
    max_reward_amount = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["threshold_min"]

    def __str__(self):
        mx = self.threshold_max if self.threshold_max is not None else "∞"
        return f"{self.threshold_min}〜{mx}"
