import calendar
from datetime import date,datetime
from django.db.models import Sum  
from django.db.models.functions import TruncMonth, Coalesce
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required 
from django . http import JsonResponse

from .forms import RecordForm
from .models import Record  
from .services import get_home_advice




# ==============================
# 分析画面で使う集計ロジック
# （表示処理は持たない）
# ==============================

def get_month_range(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end

def monthly_category_summary(user, year: int, month: int):
    start, end = get_month_range(year, month)

    return (
        Record.objects
        .filter(user=user, date__gte=start, date__lt=end)
        .values("category_id", "category__name", "category__type")  # 0=得, 1=損
        .annotate(total=Coalesce(Sum("amount"), 0))
        .order_by("category__type", "-total")
    )


# ==============================
# ホーム画面
# ==============================

@login_required
def home(request):
    today = date.today()
    first_day = today.replace(day=1)

    # 今月のレコード
    monthly_records = Record.objects.filter(
        user=request.user,
        date__gte=first_day,
        date__lte=today
    )

    # うまくいった金額（type=0）
    success_total = (
        monthly_records
        .filter(category__type=0)
        .aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # 惜しかった金額（type=1）
    regret_total = (
        monthly_records
        .filter(category__type=1)
        .aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # 今月のまとめ（差分でも合計でもOK）
    monthly_total = success_total - regret_total
    
    
    #advice_messageの取得
    advice = get_home_advice(request.user, today=today)

    return render(request, "records/home.html", {
        "success_total": success_total,
        "regret_total": regret_total,
        "monthly_total": monthly_total,
        "year": today.year,
        "month": today.month,
        "advice": advice,
    })


# ==============================
# 記録（新規入力・編集・削除）
# ==============================

#記録の追加
@login_required   
def record_create(request):
    if request.method == "POST":
        form = RecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)  # まだDBに保存しない
            record.user = request.user        # ログイン中ユーザーを入れる
            record.save()                     # ここで保存
            return redirect("records:record_create")  
    else:
        form = RecordForm()

    return render(request, "records/record_form.html", {"form": form})

@login_required
def record_list(request):
    # 今日の年月
    today = date.today()
    year = today.year
    month = today.month
    
    # ★ 追加：URLクエリから date を受け取る
    selected_date_str = request.GET.get("date")  # "2026-01-14" みたいな文字列
    selected_date = None

    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            # クリックした日付の月をカレンダー表示にも反映（便利）
            year = selected_date.year
            month = selected_date.month
        except ValueError:
            selected_date = None  # 変な値が来たら無視

    # 月のカレンダー（週単位の配列）
    cal = calendar.monthcalendar(year, month)
    
     # 月内の記録（カレンダーと同じ月を対象にするのが自然）
    month_records = (
        Record.objects
        .filter(user=request.user, date__year=year, date__month=month)
        .order_by("-date", "-created_at")
    )

    # 全件（未選択時の一覧用）
    records = Record.objects.filter(user=request.user)
    
     # 選択日の記録だけ
    selected_records = None
    if selected_date:

        selected_records = (
            Record.objects
            .filter(user=request.user, date=selected_date)
            .order_by("-created_at")
        )
    return render(request, "records/record_list.html", {
        "selected_records": selected_records,
        "records": records,
        "calendar": cal,
        "year": year,
        "month": month,
        "selected_date": selected_date,
    })


#記録の編集   
@login_required
def record_update(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)

    if request.method == "POST":
        form = RecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            return redirect("records:record_list")
    else:
        form = RecordForm(instance=record)

    return render(request, "records/record_form.html", {"form": form})


#記録の削除
@login_required
def record_delete(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)

    if request.method == "POST":
        record.delete()
        return redirect("records:record_list")

    # いったん最小：確認画面テンプレ
    return render(request, "records/record_confirm_delete.html", {"record": record})



# ==============================
# 分析画面（年次・月次）
# ==============================

#年次分析

@login_required
def analysis_year(request):
    # 今年を対象（まずは固定でOK。あとで年選択にできる）
    year = date.today().year

    qs = (
        Record.objects
        .filter(user=request.user, date__year=year)
        .annotate(month=TruncMonth("date"))
        .values("month", "category__type")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    # monthごとに「得/損」をまとめる箱を作る
    monthly = {m: {"plus": 0, "minus": 0} for m in range(1, 13)}

    for r in qs:
        m = r["month"].month
        t = r["category__type"]  # 0=得, 1=損 の想定
        total = r["total"] or 0

        if t == 0:
            monthly[m]["plus"] = total
        else:
            monthly[m]["minus"] = total


 # ===== 累計（plus - minus）を作る =====

    labels = list(range(1, 13))  # 1〜12（int）

    monthly_net = []
    cumulative_net = []

    running = 0  # 累計用の箱

    for m in labels:
        plus = monthly[m]["plus"]
        minus = monthly[m]["minus"]

        net = plus - minus      # その月の差額
        running += net          # 年始からの累計

        monthly_net.append(net)
        cumulative_net.append(running)

    # JSONで返す
    data = {
        "year": year,
        "labels": labels,
        "monthly_net": monthly_net,
        "cumulative_net": cumulative_net,
    }

    # 確認したいなら一時的にOK（不要なら消す）
    print("analysis_year data:", data)

    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})


#月次カテゴリ別分析

@login_required
def analysis_month(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    rows = monthly_category_summary(request.user, year, month)

    # 使いやすい形に整形（得/損に分ける）
    data = {"year": year, "month": month, "success": [], "regret": []}
    for r in rows:
        item = {"name": r["category__name"], "total": int(r["total"] or 0)}
        if r["category__type"] == 0:
            data["success"].append(item)
        else:
            data["regret"].append(item)

    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})

    