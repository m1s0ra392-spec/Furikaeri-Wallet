#第２のviews.py
#おもにadcvice_masssageについて

from dataclasses import dataclass
from datetime import date
from django.db.models import Sum
from .models import Record, AdviceMessage


# ==============================
# Admin から文言増やすロジック等
# ==============================

@dataclass
class AdviceResult:
    message: str
    diff: int
    reward_amount: int | None

def _calc_monthly_diff(user, today: date) -> int:
    """
    今月の差分（余裕/赤字）を計算する。
    ここはあなたの定義に合わせて調整OK。

    例：
    - success(type=0) が「プラス（得）」の合計
    - regret(type=1) が「マイナス（損）」の合計
    - 差分 = success_total - regret_total
    """
    first_day = today.replace(day=1)
    qs = Record.objects.filter(user=user, date__gte=first_day, date__lte=today)

    success_total = qs.filter(category__type=0).aggregate(total=Sum("amount"))["total"] or 0
    regret_total = qs.filter(category__type=1).aggregate(total=Sum("amount"))["total"] or 0

    return int(success_total - regret_total)

def get_home_advice(user, today: date | None = None) -> AdviceResult | None:
    today = today or date.today()
    diff = _calc_monthly_diff(user, today)

    # diff が範囲内のものを1件取る
    advice = (
        AdviceMessage.objects
        .filter(threshold_min__lte=diff)
        .filter(threshold_max__gte=diff)  # threshold_max が NULL のものが落ちるので後でORする
        .first()
    )

    if advice is None:
        advice = (
            AdviceMessage.objects
            .filter(threshold_min__lte=diff, threshold_max__isnull=True)
            .order_by("threshold_min")
            .first()
        )

    if advice is None:
        return None  # まだDBが空なら何も出さない

    reward_amount = None
    if advice.needs_calculation:
        # 例：余裕(diff)の30%を還元提案。ただし diff<=0 なら 0扱い
        base = max(diff, 0)
        reward_amount = int(base * 0.3)

        if advice.max_reward_amount is not None:
            reward_amount = min(reward_amount, advice.max_reward_amount)

    # message_content にプレースホルダを使えるようにする
    # 例：「今月は余裕あり！{reward_amount}円でカフェでもどう？」
    message = advice.message_content.format(
        diff=diff,
        reward_amount=reward_amount if reward_amount is not None else "",
    )

    return AdviceResult(message=message, diff=diff, reward_amount=reward_amount)