from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from .models import Topic


@login_required
def topic_list(request):
    category = request.GET.get("category")  # "0"/"1"/"2"/None
    sort = request.GET.get("sort", "popular")  # "popular" or "new"（トップは人気が初期）

    qs = (
        Topic.objects
        .filter(status=Topic.Status.PUBLIC)
        .select_related("user")
    )

    is_category_page = category in {"0", "1", "2"}

    # --- カテゴリ絞り込み ---
    if is_category_page:
        qs = qs.filter(board_category=int(category))
        # カテゴリ内は一旦 新着順でOK（人気順も後で可能）
        qs = qs.order_by("-created_at")

    # --- トップ（全カテゴリ横断の並び替え） ---
    else:
        if sort == "new":
            qs = qs.order_by("-created_at")
        else:
            # popular（いいね数順）は Like モデルができたらここを本実装する
            # いまは仮で新着順でもOK。Like導入後に↓を有効化するイメージ。
            # qs = qs.annotate(like_count=Count("likes")).order_by("-like_count", "-created_at")
            qs = qs.order_by("-created_at")

        qs = qs[:20]  # ★トップは最大20件

    context = {
        "topics": qs,
        "selected_category": category,
        "categories": Topic.BoardCategory.choices,
        "sort": sort,
        "is_category_page": is_category_page,
    }
    return render(request, "board/topic_list.html", context)
