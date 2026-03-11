
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Exists, OuterRef
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from django.utils import timezone

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
def topic_detail(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
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



# ==================================
# トピック作成（新規・編集のベース）　
# ==================================

@login_required
def topic_save(request, pk=None):
    topic = None
    if pk is not None:
        topic = get_object_or_404(Topic, pk=pk, user=request.user)

    if request.method == "POST":
        print("action =", request.POST.get("action"))
        
        form = TopicForm(request.POST, instance=topic)
        action = request.POST.get("action")  # "draft" / "confirm"

        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user

            if action == "draft":
                obj.status = Topic.TopicStatus.DRAFT
                obj.save()
                form.save_m2m()
                return redirect("board:mypage_drafts")

            if action == "confirm":
                # 新規でもpkを持たせるため、一旦DRAFTとして保存
                if obj.pk is None:
                    obj.status = Topic.TopicStatus.DRAFT
                    obj.save()
                    form.save_m2m()
                else:
                    obj.save()
                    form.save_m2m()

                return render(request, "board/topic_confirm.html", {
                    "form": form,
                    "topic": obj,
                    "category_label": obj.get_board_category_display(),
                    "tags": form.cleaned_data.get("tags", []),
                    "mode": "create" if pk is None else "edit",
                })

    else:
        form = TopicForm(instance=topic)

    return render(request, "board/topic_form.html", {
        "form": form,
        "topic": topic,
        "mode": "create" if pk is None else "edit",
        "primary_label": "確認画面へ",
        "show_draft_button": True,
        "show_delete_request": False,
    })

# ==============================
# トピック投稿前確認
# ==============================

@login_required
def topic_confirm(request, pk):
    topic = get_object_or_404(Topic, pk=pk, user=request.user)

    # POST（確認画面のボタン）
    if request.method == "POST":
        action = request.POST.get("action")
        print("topic_confirm action =", action)
        
        if action == "back":
            # 下書き編集に戻す（draft_topic_edit を使う方針なら）
            if topic.status == Topic.TopicStatus.DRAFT:
                return redirect("board:draft_topic_edit", pk=topic.pk)
            # 公開済みなら topic_edit に戻す
            return redirect("board:topic_edit", pk=topic.pk)

        if action == "post":
            form = TopicForm(request.POST, instance=topic)
            
            print("POST title =", request.POST.get("title"))
            print("POST text =", request.POST.get("text"))
            print("POST tags =", request.POST.getlist("tags"))

            if form.is_valid():
                obj = form.save(commit=False)
                obj.user = request.user
                obj.status = Topic.TopicStatus.PUBLIC
                obj.save()
                form.save_m2m()
                return redirect("board:topic_detail", pk=obj.pk)
            
            print("form errors =", form.errors)

        print("redirect confirm again")

        # action不明なら確認に戻す
        return redirect("board:topic_confirm", pk=topic.pk)

    # GET（確認表示）
    form = TopicForm(instance=topic)
    category_label = topic.get_board_category_display()

    return render(request, "board/topic_confirm.html", {
        "form": form,
        "topic": topic,
        "category_label": category_label,
        "tags": getattr(topic, "tags", None).all() if hasattr(topic, "tags") else [],
    })

# ==============================
# 下書きトピック編集
# ==============================

@login_required
def draft_topic_edit(request, pk):
    # 本人の「下書き」だけ取る
    topic = get_object_or_404(
        Topic,
        pk=pk,
        user=request.user,
        status=Topic.TopicStatus.DRAFT, 
    )

    if request.method == "POST":
        form = TopicForm(request.POST, instance=topic)
        action = request.POST.get("action")  # "draft" or "confirm" 

        if form.is_valid():
            if action == "draft":
                obj = form.save(commit=False)
                obj.user = request.user
                obj.status = Topic.TopicStatus.DRAFT
                obj.save()
                form.save_m2m()
                return redirect("board:mypage_drafts")

            if action == "confirm":
                return render(request, "board/topic_confirm.html", {
                    "form": form,
                    "topic": topic,
                    "category_label": topic.get_board_category_display(),
                    "tags": form.cleaned_data.get("tags", []),
                    "mode": "draft_edit",
                })

    else:
        form = TopicForm(instance=topic)

    return render(request, "board/topic_form.html", {
        "form": form,
        "topic": topic,
        "mode": "draft_edit",
        "primary_label": "確認画面へ",
        "show_draft_button": True,
        "show_delete_request": False,
    })
    

# ==============================
# 下書きトピック削除
# ==============================

@login_required
def draft_topic_delete(request, pk):
    # 本人の「下書き」だけ取る（他人のや公開済みは触れない）
    topic = get_object_or_404(
        Topic,
        pk=pk,
        user=request.user,
        status=Topic.TopicStatus.DRAFT,
    )

    if request.method == "POST":
        topic.delete()
        return redirect("board:mypage_drafts")

    # GETで来た場合はそのまま下書き一覧へ（モーダルで確認するのでGETは使わない）
    return redirect("board:mypage_drafts")


# ==============================
# トピック編集(作成済み)
# ==============================

@login_required
def topic_edit(request, pk):
    # ここで本人の投稿しか取れない
    topic = get_object_or_404(Topic, pk=pk, user=request.user)

    if request.method == "POST":
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.status = Topic.TopicStatus.PUBLIC 
            topic.save()
            form.save_m2m()
            return redirect("board:topic_detail", pk=topic.id)  
    else:
        form = TopicForm(instance=topic)

    return render(request, "board/topic_form.html", {
        "form": form,
        "topic": topic,
        "mode": "edit",
        "primary_label": "トピックを更新する",
        "show_draft_button": False,
        "show_delete_request": True,
    })

# ==============================
# トピック削除要請
# ==============================

@login_required
def topic_delete_request(request, pk):
    topic = get_object_or_404(Topic, pk=pk, user=request.user)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()

        # 仮：理由必須だけチェック（保存はまだしない）
        if not reason:
            return render(request, "board/topic_delete_confirm.html", {
                "topic": topic,
                "error": "削除の理由は必須です。",
            })

        # 仮：送信完了ページへ
        return render(request, "board/topic_delete_requested.html", {
            "topic": topic,
        })

    # GET：確認ページ
    return render(request, "board/topic_delete_confirm.html", {
        "topic": topic,
    })



# ==============================
# コメント新規作成（新規・下書き編集のベース）
# ==============================

@login_required
def comment_save(request, topic_pk, pk=None):
    """
    pk=None  → 新規作成
    pk=あり  → 下書き編集
    トピックの topic_save と同じ構造にしている
    """
    topic = get_object_or_404(Topic, pk=topic_pk)
    comment = None

    if pk is not None:
        # 下書き編集：本人の下書きだけ取れる
        comment = get_object_or_404(
            Comment,
            pk=pk,
            user=request.user,
            status=Comment.CommentStatus.DRAFT,
        )

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        action = request.POST.get("action")  # "draft" / "confirm"

        if form.is_valid():
            obj = form.save(commit=False)
            obj.topic = topic
            obj.user = request.user

            # 返信番号 → parent_comment に変換
            reply_to_seq = form.cleaned_data.get("reply_to")
            if reply_to_seq:
                parent = Comment.objects.filter(
                    topic=topic, sequence=reply_to_seq
                ).first()
                if not parent:
                    form.add_error(
                        "reply_to",
                        f"#{reply_to_seq} のコメントが見つかりません",
                    )
                    return render(request, "board/comment_form.html", {
                        "form": form,
                        "topic": topic,
                        "comment": comment,
                        "mode": "create" if pk is None else "draft_edit",
                    })
                obj.parent_comment = parent

            # ── 下書き保存 ──────────────────────────
            if action == "draft":
                # sequence はまだ採番しない（公開時に採番）
                if obj.pk is None:
                    obj.sequence = 0  # 仮置き（公開時に上書きされる）

                obj.status = Comment.CommentStatus.DRAFT
                obj.save()
                return redirect("board:mypage_drafts")

            # ── 確認画面へ ──────────────────────────
            if action == "confirm":
                # 新規の場合は一旦 DRAFT で保存してから確認画面へ
                # （トピックの topic_save と同じ方式）
                if obj.pk is None:
                    obj.sequence = 0  # 仮置き
                    obj.status = Comment.CommentStatus.DRAFT
                    obj.save()
                else:
                    obj.save()

                return render(request, "board/comment_confirm.html", {
                    "form": form,
                    "topic": topic,
                    "comment": obj,
                    "mode": "create" if pk is None else "draft_edit",
                })

    else:
        form = CommentForm(instance=comment)

    return render(request, "board/comment_form.html", {
        "form": form,
        "topic": topic,
        "comment": comment,
        "mode": "create" if pk is None else "draft_edit",
        "show_draft_button": True,
    })


# ==============================
# コメント投稿前確認
# ==============================

@login_required
def comment_confirm(request, pk):
   
    comment = get_object_or_404(Comment, pk=pk, user=request.user)
    topic = comment.topic

    if request.method == "POST":
        action = request.POST.get("action")

        # ── 戻る ─────────────────────────────────
        if action == "back":
            if comment.status == Comment.CommentStatus.DRAFT:
                # 下書き編集から来た場合
                if comment.created_at != comment.updated_at:
                    return redirect("board:comment_save_edit", topic_pk=topic.pk, pk=comment.pk)
                # 新規から来た場合
                return redirect("board:comment_save_new", topic_pk=topic.pk)
            # 公開済みから来た場合
            return redirect("board:comment_edit", pk=comment.pk)

        # ── 投稿 ─────────────────────────────────
        if action == "post":
            form = CommentForm(request.POST, instance=comment)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.status = Comment.CommentStatus.PUBLIC

                # 公開時に初めて sequence を採番
                max_seq = Comment.objects.filter(
                    topic=topic,
                    status=Comment.CommentStatus.PUBLIC  # 公開済みだけでカウント
                ).aggregate(Max("sequence"))["sequence__max"]
                obj.sequence = (max_seq or 0) + 1

                obj.save()
                return redirect("board:topic_detail", pk=topic.pk)

    # GET：確認表示
    form = CommentForm(instance=comment)
    return render(request, "board/comment_confirm.html", {
        "form": form,
        "topic": topic,
        "comment": comment,
    })


# ==============================
# コメント編集（投稿済み）
# ==============================

@login_required
def comment_edit(request, pk):
    """
    トピックの topic_edit と同じ構造。
    投稿済みコメントの編集 → 確認画面 → 更新。
    """
    comment = get_object_or_404(
        Comment,
        pk=pk,
        user=request.user,
        status=Comment.CommentStatus.PUBLIC,
    )
    topic = comment.topic

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        action = request.POST.get("action")

        if form.is_valid():
            obj = form.save(commit=False)

            # ── 確認画面へ ──────────────────────────
            if action == "confirm":
                obj.save()
                return render(request, "board/comment_confirm.html", {
                    "form": form,
                    "topic": topic,
                    "comment": obj,
                    "mode": "edit",
                })

    else:
        form = CommentForm(instance=comment)

    return render(request, "board/comment_form.html", {
        "form": form,
        "topic": topic,
        "comment": comment,
        "mode": "edit",
        "primary_label": "確認画面へ",
        "show_draft_button": False,
        "show_delete_button": True,   # ← 削除ボタンを表示
    })


# ==============================
# コメント削除（投稿済み・論理削除）
# ==============================

@login_required
def comment_delete(request, pk):
    """
    トピックの下書き削除（draft_topic_delete）と同じ構造。
    投稿済みは論理削除（is_deleted=True）にする。
    他ユーザーのコメントへの返信が残るため物理削除ではなく論理削除。
    """
    comment = get_object_or_404(
        Comment,
        pk=pk,
        user=request.user,
        status=Comment.CommentStatus.PUBLIC,
    )

    if request.method == "POST":
        comment.is_deleted = True
        comment.deleted_at = timezone.now()
        comment.deleted_by = request.user
        comment.save()
        return redirect("board:mypage_comments")

    return redirect("board:mypage_comments")


# ==============================
# 下書きコメント削除（物理削除）
# ==============================

@login_required
def draft_comment_delete(request, pk):
    """
    draft_topic_delete と完全に同じ構造。
    下書きは他ユーザーに影響がないので物理削除でOK。
    """
    comment = get_object_or_404(
        Comment,
        pk=pk,
        user=request.user,
        status=Comment.CommentStatus.DRAFT,
    )

    if request.method == "POST":
        comment.delete()
        return redirect("board:mypage_drafts")

    return redirect("board:mypage_drafts")

# ==============================
# いいねの追加・解除
# ==============================

@require_POST
@login_required
def topic_like_toggle(request, pk):
    topic = get_object_or_404(Topic, pk=pk)

    like, created = TopicLike.objects.get_or_create(
        user=request.user,
        topic=topic,
    )

    if not created:
        # 既にあった = いいね取り消し
        like.delete()

    # 押した元のページへ戻す（HTTP_REFERERが無い場合の保険で詳細へ）
    return redirect(request.META.get("HTTP_REFERER", "board:topic_detail"), pk=topic.id)


@require_POST
@login_required
def comment_like_toggle(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    like, created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment,
    )

    if not created:
        like.delete()

    # コメントは基本トピック詳細に戻すのが自然
    return redirect(request.META.get("HTTP_REFERER", "board:topic_detail"), pk=comment.pk)


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



# ==============================
# 掲示板マイページ
# ==============================

@login_required
def mypage_index(request):
    # 最初のページは「私のいいね」
    return redirect("board:mypage_likes")


#「わたしのいいね」
@login_required
def mypage_likes(request):
    user = request.user

    # いいねしたトピック（いいね日時の新しい順）
    liked_topics = (
        Topic.objects.filter(likes__user=user)  
        .select_related("user")
        .order_by("-likes__created_at")
        .distinct() #重複対策
    )

    # いいねしたコメント（いいね日時の新しい順）
    liked_comments = (
        Comment.objects.filter(likes__user=user)  
        .select_related("user", "topic")
        .order_by("-likes__created_at")
        .distinct() #重複対策
    )

    return render(request, "board/mypage_likes.html", {
        "tab": "likes",
        "liked_topics": liked_topics,
        "liked_comments": liked_comments,
    })


#「私のトピック」

@login_required
def mypage_topics(request):
    topics = (
        Topic.objects
        .filter(user=request.user, status=Topic.TopicStatus.PUBLIC)  # 投稿済み＝公開
        .order_by("-created_at")
    )

    return render(request, "board/mypage_topics.html", {
        "topics": topics,
    })
    

#「私のコメント」

@login_required
def mypage_comments(request):
    comments = (
        Comment.objects
        .filter(user=request.user)
        .select_related("topic")   # topic を一緒に取ってDB回数減らす
        .order_by("-created_at")
    )

    return render(request, "board/mypage_comments.html", {
        "comments": comments,
    })
    
    
#「下書き一覧」

@login_required
def mypage_drafts(request):
    draft_topics = Topic.objects.filter(
        user=request.user,
        status=Topic.TopicStatus.DRAFT
    ).order_by("-updated_at")

    draft_comments = Comment.objects.filter(
        user=request.user,
        status=Comment.CommentStatus.DRAFT
    ).order_by("-updated_at")

    return render(request, "board/mypage_drafts.html", {
        "tab": "drafts",
        "draft_topics": draft_topics,
        "draft_comments": draft_comments,
    })
    

