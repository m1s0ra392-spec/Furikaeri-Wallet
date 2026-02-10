
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Exists, OuterRef
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET

from collections import defaultdict

from .models import Topic, Comment, TopicLike, CommentLike, Tag
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
        .filter(status=Topic.TopicStatus.PUBLIC)
        .select_related("user")
        .annotate(
            like_count=Count("likes", distinct=True),
            is_liked=Exists(
                TopicLike.objects.filter(topic=OuterRef("pk"), user=request.user)
        ),
    ))

    is_category_page = category in {"0", "1", "2"}

    # --- カテゴリ絞り込み ---
    if is_category_page:
        qs = qs.filter(board_category=int(category))
        # カテゴリ内は一旦 新着順でOK（人気順も後で可能）
        qs = qs.order_by("-created_at")

    # --- トップ（全カテゴリ横断の並び替え） ---
    else:
        if sort == "new":
            qs = qs.order_by("-created_at")   #新着順
        else:
            qs = qs.order_by("-created_at")   #いいね順

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
# トピック詳細ビュー
# ==============================

@login_required
def topic_detail(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    # topic のいいね数
    topic_like_count = TopicLike.objects.filter(topic=topic).count()

    # 自分がこのトピックをいいねしてるか
    is_topic_liked = TopicLike.objects.filter(topic=topic, user=request.user).exists()

    comments = (
        Comment.objects
        .filter(topic=topic, status=Comment.CommentStatus.PUBLIC)
        .select_related("user", "parent_comment")
        .annotate(
        like_count=Count("likes", distinct=True),  
        is_liked=Exists(
            CommentLike.objects.filter(comment=OuterRef("pk"), user=request.user)
        ),
    )
        .order_by("sequence")
    )

    return render(request, "board/topic_detail.html", {
        "topic": topic,
        "topic_like_count": topic_like_count,
        "is_topic_liked": is_topic_liked,
        "comments": comments,
    })



# ==============================
# トピック作成
# ==============================

@login_required
def topic_create(request):
    if request.method == "POST":
        form = TopicForm(request.POST)
        action = request.POST.get("action")  # confirm / draft

        if form.is_valid():
            topic = form.save(commit=False)
            topic.user = request.user  # user紐付け

            if action == "draft":
                topic.status = Topic.TopicStatus.DRAFT   
                topic.save()
                return redirect("board:topic_edit", topic.id)  # 下書き編集画面など
            else:
                topic.status = Topic.TopicStatus.PUBLIC  # 投稿は公開にする
                topic.save()
                return redirect("board:topic_confirm", topic.id)  

    else:
        form = TopicForm()

    return render(request, "topics/topic_form.html", {"form": form})


# ==============================
# トピック投稿前確認
# ==============================

@login_required
def topic_confirm(request, pk):
    topic = get_object_or_404(Topic, pk=pk, user=request.user)

    # GETだけでOK（まずは）
    return render(request, "topics/topic_confirm.html", {
        "topic": topic
    })
    

# ==============================
# コメント作成
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
            
            # ★押したボタンでステータス決定
            action = request.POST.get("action")
            if action == "post":
                comment.status = Comment.CommentStatus.PUBLIC
            else:
                comment.status = Comment.CommentStatus.DRAFT
            
            # 返信番号（任意）→ parent に変換
            reply_to_seq = form.cleaned_data.get("reply_to")   #返信番号を取り出す
            if reply_to_seq:    #返信番号が入っていれば処理する、空欄ならば通常コメント
                parent = Comment.objects.filter(topic=topic, sequence=reply_to_seq).first()
                if not parent:  #存在しない返信番号の反映を防ぐ
                    form.add_error("reply_to", f"#{reply_to_seq} のコメントが見つかりません")
                    return render(request, "board/comment_form.html", {"form": form, "topic": topic})
                comment.parent_comment = parent
                

            # sequence 自動採番（topic内でMax+1）
            max_sequence = (
                Comment.objects
                .filter(topic=topic)
                .aggregate(Max("sequence"))["sequence__max"]
            )

            comment.sequence = (max_sequence or 0) + 1
            

            comment.save()
            return redirect("board:topic_detail", topic_id=topic.id)
    else:
        form = CommentForm()

    return render(request, "board/comment_form.html", {
        "form": form,
        "topic": topic,
    })  
    


# ==============================
# いいねの追加・解除
# ==============================

@require_POST
@login_required
def topic_like_toggle(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)

    like, created = TopicLike.objects.get_or_create(
        user=request.user,
        topic=topic,
    )

    if not created:
        # 既にあった = いいね取り消し
        like.delete()

    # 押した元のページへ戻す（HTTP_REFERERが無い場合の保険で詳細へ）
    return redirect(request.META.get("HTTP_REFERER", "board:topic_detail"), topic_id=topic.id)


@require_POST
@login_required
def comment_like_toggle(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)

    like, created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment,
    )

    if not created:
        like.delete()

    # コメントは基本トピック詳細に戻すのが自然
    return redirect(request.META.get("HTTP_REFERER", "board:topic_detail"), topic_id=comment.topic_id)


# ==============================
# タグ検索
# ==============================

@login_required
@require_GET
def tag_search_api(request):
    """
    入力文字列 q をもとに既存タグ候補を返すAPI
    GET /board/api/tags/?q=xxx
    戻り値: [{"id": 1, "name": "節約"}, ...]
    """
    q = (request.GET.get("q") or "").strip()

    # 空なら空配列（候補を出さない）
    if not q:
        return JsonResponse([], safe=False)

    qs = (
        Tag.objects
        .filter(name__istartswith=q)
        .order_by("name")
        .values("id", "name")[:10]
    )

    return JsonResponse(list(qs), safe=False)