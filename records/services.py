# ホーム画面にだす”アドバイスの文面”を、
#「今月の収支の差分」に応じてＤＢから選んで返すロジック


from dataclasses import dataclass
from datetime import date
from django.db.models import Sum
from .models import Record, AdviceMessage
import random
from django.db.models import Q


# ==============================
# Admin から文言増やすロジック等
# ==============================


# ---- 返り値（viewに渡すデータ構造）----
@dataclass
class AdviceResult:
    message: str
    diff: int
    reward_amount: int | None


# ---- 今月の差分(diff)計算：得（type=0）- 損（type=1）----
def _calc_monthly_diff(user, today: date) -> int:
    first_day = today.replace(day=1)
    qs = Record.objects.filter(user=user, date__gte=first_day, date__lte=today)

    success_total = qs.filter(category__type=0).aggregate(total=Sum("amount"))["total"] or 0
    regret_total = qs.filter(category__type=1).aggregate(total=Sum("amount"))["total"] or 0

    return int(success_total - regret_total)


# ---- ホームに出すアドバイス選定（DB検索→1件選択→整形）----
def get_home_advice(user, today: date | None = None) -> AdviceResult | None:
    
     # 1) diffを計算
    today = today or date.today()
    diff = _calc_monthly_diff(user, today)
    
    # 2) diffの範囲に合うメッセージ候補をDBから取得（maxがNULL=上限なしも含む）
    candidates = AdviceMessage.objects.filter(
    threshold_min__lte=diff
    ).filter(
    Q(threshold_max__gte=diff) | Q(threshold_max__isnull=True)
)

    if not candidates.exists():
        return None  # まだDBが空 or 条件に当てはまるものがない

    # 3) 候補からランダムに1件選ぶ
    ids = list(candidates.values_list("id", flat=True))
    picked_id = random.choice(ids)
    advice = candidates.get(id=picked_id)
    
    # 4) 必要なら還元額を計算
    reward_amount = None
    if advice.needs_calculation:
        # 例：余裕(diff)の30%を還元提案。ただし diff<=0 なら 0扱い
        base = max(diff, 0)
        reward_amount = int(base * 0.3)

        if advice.max_reward_amount is not None:
            reward_amount = min(reward_amount, advice.max_reward_amount)#上限をかける

    
    # 5) 文言のプレースホルダを埋めて返す
    # message_content で使ってよいプレースホルダ：
    # - {diff}
    # - {reward_amount}
    message = advice.message_content.format(
        diff=diff,
        reward_amount=reward_amount if reward_amount is not None else "",
    )

    return AdviceResult(message=message, diff=diff, reward_amount=reward_amount)