
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.shortcuts import render

from .models import Topic, Comment
from .forms import TopicForm, CommentForm

# ==============================
# 掲示板トップ　トピックの選定
# ==============================

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



# ==============================
# トピック作成ビュー
# ==============================

@login_required
def topic_create(request):
    if request.method == "POST":
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.user = request.user
            topic.save()
            return redirect("board:topic_list")  # 一旦一覧へ（のちに確認画面→トピック内容画面へ）
    else:
        form = TopicForm()

    return render(request, "board/topic_form.html", {
        "form": form
    })
    
 
# ==============================
# トピック詳細
# ==============================

@login_required
def topic_detail(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    return render(request, "board/topic_detail.html", {"topic": topic})
 
 
# ==============================
# コメント作成ビュー
# ==============================
    
@login_required    
def comment_create(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.topic = topic
            comment.user = request.user 

            # sequence 自動採番（topic内でMax+1）
            max_sequence = (
                Comment.objects
                .filter(topic=topic)
                .aggregate(Max("sequence"))["sequence__max"]
            )

            comment.sequence = (max_sequence or 0) + 1
            
            # 返信番号（任意）→ parent に変換
            reply_to_seq = form.cleaned_data.get("reply_to")   #返信番号を取り出す
            if reply_to_seq:    #返信番号が入っていれば処理する、空欄ならば通常コメント
                parent = Comment.objects.filter(topic=topic, sequence=reply_to_seq).first()
                if not parent:  #存在しない返信番号の反映を防ぐ
                    form.add_error("reply_to", f"#{reply_to_seq} のコメントが見つかりません")
                    return render(request, "board/comment_form.html", {"form": form, "topic": topic})
                comment.parent = parent

            comment.save()
            return redirect("board:topic_detail", topic_id=topic.id)
    else:
        form = CommentForm()

    return render(request, "board/comment_form.html", {
        "form": form,
        "topic": topic,
    })  