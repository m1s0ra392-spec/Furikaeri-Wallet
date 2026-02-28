
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Exists, OuterRef
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
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



# ==============================
# トピック作成　※入力するだけ　保存はしていない
# ==============================

SESSION_KEY = "topic_confirm_data"

@login_required
def topic_create(request):
    data = request.session.get(SESSION_KEY)

    if data:
        # セッションから復元（タグは文字列でもOK）
        initial = {
            "board_category": data.get("board_category", ""),
            "title": data.get("title", ""),
            "text": data.get("text", ""),
            "tags": [str(t) for t in data.get("tags", [])],
        }
        form = TopicForm(initial=initial)
        
    else:
        form = TopicForm()
            
    return render(request, "board/topic_form.html", {
        "form": form,
        "mode": "create",
        "primary_label": "確認画面へ",
        "show_draft_button": True,     # ★新規作成で下書きボタン表示
        "show_delete_request": False,  # 新規では削除申請なし
    })


# ==============================
# トピック投稿前確認 ※ここで保存する分岐
# ==============================

@login_required
def topic_confirm(request):
    # POST: 入力→確認 or 投稿確定
    if request.method == "POST":
        action = request.POST.get("action")
        
        
        # 確認画面→戻る
        if action == "back":
            # セッションは消さない（入力保持のため）
            return redirect("board:topic_create")
        
        # --- 下書き保存は「入力画面で行いたい」ので、ここでは処理しない方針でもOK ---
        # もし topic_form.html が confirm に投げるなら、draft もここで拾う必要がある
        if action == "draft":
            form = TopicForm(request.POST)
            if form.is_valid():
                topic = form.save(commit=False)
                topic.user = request.user
                topic.status = Topic.TopicStatus.DRAFT
                topic.save()
                form.save_m2m()
                request.session.pop(SESSION_KEY, None)
                return redirect("board:mypage_drafts")
            return render(request, "board/topic_form.html", {
                "form": form,
                "mode": "create",
                "primary_label": "確認画面へ",
                "show_draft_button": True,
            })

        # --- 入力 → 確認（POSTあり）---
        if action == "confirm":
            form = TopicForm(request.POST)
            if not form.is_valid():
                return render(request, "board/topic_form.html", {
                    "form": form,
                    "mode": "create",
                    "primary_label": "確認画面へ",
                    "show_draft_button": True,
                })

            # tagsは複数なので list で保存
            board_category = form.cleaned_data["board_category"]
            request.session[SESSION_KEY] = {
                "board_category": int(board_category),
                "title": form.cleaned_data["title"],
                "text": form.cleaned_data["text"],
                "tags": [t.id for t in form.cleaned_data.get("tags")],
                 "status": Topic.TopicStatus.PUBLIC, 
            }
            # ✅ 事故防止：POSTのままrenderせず、GETへ逃がす（更新事故/再送信防止）
            request.session.modified = True
            return redirect("board:topic_confirm")

        # --- 投稿確定（confirm画面の「投稿する」）---
        if action == "post":
            data = request.session.get(SESSION_KEY)
            if not data:
                return redirect("board:topic_create")

            form = TopicForm(data)
            if not form.is_valid():
                # セッション壊れ等
                return redirect("board:topic_create")

            topic = form.save(commit=False)
            topic.user = request.user
            topic.status = Topic.TopicStatus.PUBLIC
            topic.save()
            form.save_m2m()

            request.session.pop(SESSION_KEY, None)
            return redirect("board:topic_detail", pk=topic.id)

        # action不明なら入力へ
        return redirect("board:topic_create")

    # ==========
    # GET: 確認表示
    # ==========
    data = request.session.get(SESSION_KEY)
    print("GET confirm session data:", data)
    
    if not data:
        print("NO SESSION DATA -> redirect create")
        return redirect("board:topic_create")
    
    form = TopicForm(data)
    print("GET confirm form valid:", form.is_valid())
    print("GET confirm errors:", form.errors)
    if not form.is_valid():
        return redirect("board:topic_create")

    # ✅ ①カテゴリID→ラベル
    category_value = form.cleaned_data["board_category"]
    category_label = Topic.BoardCategory(int(category_value)).label

    return render(request, "board/topic_confirm.html", {
        "form": form,
        "category_label": category_label,
        "tags": form.cleaned_data.get("tags"),
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
        action = request.POST.get("action")  # "draft" or "post" を想定

        if form.is_valid():
            topic = form.save(commit=False)
            topic.user = request.user  # 念のため固定

            if action == "draft":
                topic.status = Topic.TopicStatus.DRAFT
                topic.save()
                form.save_m2m()
                return redirect("board:mypage_drafts")
            
            topic.status = Topic.TopicStatus.PUBLIC
            topic.save()
            form.save_m2m()
            return redirect("board:topic_confirm", pk=topic.id)

    else:
        form = TopicForm(instance=topic)

    return render(request, "board/topic_form.html", {
        "form": form,
        "topic": topic,
        "mode": "draft_edit",
        "primary_label": "トピックを投稿する",
        "show_draft_button": True,     # 下書きボタンを出したい
        "show_delete_request": False,  # 下書きは削除申請なし（おすすめ）
    })
    


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
# トピック編集（削除要請）
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
# コメント作成
# ==============================
    
@login_required    
def comment_create(request, pk):
    topic = get_object_or_404(Topic, pk=pk)

    if request.method == "POST":
        form = CommentForm(request.POST)
        action = request.POST.get("action")  #"post" or "draft"
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.topic = topic
            comment.user = request.user 
            

            # 返信番号（任意）→ parent に変換
            reply_to_seq = form.cleaned_data.get("reply_to")   #返信番号を取り出す
            if reply_to_seq:    #返信番号が入っていれば処理する、空欄ならば通常コメント
                parent = Comment.objects.filter(topic=topic, sequence=reply_to_seq).first()
                if not parent:  #存在しない返信番号の反映を防ぐ
                    form.add_error("reply_to", f"#{reply_to_seq} のコメントが見つかりません")
                    return render(request, "board/comment_form.html", {"form": form, "topic": topic})
                comment.parent_comment = parent
                

            # sequence 自動採番（topic内でMax+1）※新規作成時に限り
            max_sequence = (
                Comment.objects
                .filter(topic=topic)
                .aggregate(Max("sequence"))["sequence__max"]
            )

            comment.sequence = (max_sequence or 0) + 1
            
            #コメント投稿前に確認挟む
            comment.status = Comment.CommentStatus.DRAFT
            comment.save()

            if action == "post":
                return redirect("board:comment_confirm", pk=comment.id)

            # action == "draft"
           # return redirect("board:comment_edit", pk=comment.id)
        
    else:
        form = CommentForm()

    return render(request, "board/comment_form.html", {
        "form": form,
        "topic": topic,
    })  


# ==============================
# コメント確認
# ==============================

@login_required
def comment_confirm(request, pk):
    topic = get_object_or_404(Topic, pk=pk)

    if request.method != "POST":
        return redirect("board:comment_create", pk=topic.pk)

    action = request.POST.get("action")  # confirm / back / post
    form = CommentForm(request.POST)

    if not form.is_valid():
        return render(request, "board/comment_form.html", {
            "topic": topic,
            "form": form,
        })

    # ✅ 追加：確認画面を表示
    if action == "confirm":
        return render(request, "board/comment_confirm.html", {
            "topic": topic,
            "form": form,
        })

    # ✅ 戻る：入力画面へ（入力保持）
    if action == "back":
        return render(request, "board/comment_form.html", {
            "topic": topic,
            "form": form,
        })

    # ✅ 投稿：保存して詳細へ
    if action == "post":
        comment = form.save(commit=False)
        comment.topic = topic
        comment.user = request.user
        comment.status = Comment.CommentStatus.PUBLIC
        
        # ✅ sequence を採番（topic内で連番）
        last_seq = Comment.objects.filter(topic=topic).aggregate(Max("sequence"))["sequence__max"]
        comment.sequence = (last_seq or 0) + 1
    
        comment.save()
        messages.success(request, "コメントを投稿しました。")
        return redirect("board:topic_detail", pk=topic.pk)

    return redirect("board:comment_create", pk=topic.pk)


# ==============================
#　コメント編集
# ==============================

@login_required
def comment_edit(request, pk):
    comment = get_object_or_404(Comment, pk=pk, user=request.user)

    form = CommentForm(instance=comment)

    return render(request, "board/comment_form.html", {
        "form": form,
        "topic": comment.topic,   # テンプレで「どのトピックのコメントか」出したい時用
        "mode": "edit",
        "primary_label": "コメントを更新する",
        "show_draft_button": False,  # ひとまずトピックと合わせて制御（必要なら後でON）
        "comment": comment,          # 既存値表示などに使う
    })

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
    


@login_required
def draft_comment_edit_dummy(request, pk):
    return HttpResponse("仮：コメント編集画面")