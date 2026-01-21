from django.db import models
from users.models import User


#ER図：categories
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



#ER図:records
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
    memo = models.CharField(max_length=200, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} {self.category.name} {self.amount}"