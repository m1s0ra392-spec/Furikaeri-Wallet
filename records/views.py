import calendar
from datetime import date,datetime
from django.db.models import Sum  
from django.db.models.functions import TruncMonth, Coalesce
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required 
from django . http import JsonResponse

from django.db import models

from .forms import RecordForm
from .models import Record, RecordCategory
from .services import get_home_advice

from django.views.generic import TemplateView
from django.shortcuts import redirect



# ==============================
# ポートフォリオページ用
# ==============================
class PortfolioView(TemplateView):
    template_name = "portfolio.html"

def furikaeri_wallet_redirect(request):
    if request.user.is_authenticated:
        return redirect('records:home')  # ホーム画面
    else:
        return redirect('login')  # ログイン画面

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
    saved = False  
    return_to_calendar = False
        
    if request.method == "POST":
        form = RecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.user = request.user
            record.save()
            form = RecordForm()
            # 「続けて入力」ボタンが押された場合
            if request.POST.get("continue"):
                saved = True
                return_to_calendar = False  # ← カレンダーには戻らない
            else:
                saved = True
                return_to_calendar = True
         # バリデーションエラーの場合はformをそのまま使う
    else:
        form = RecordForm()        
    
    # タブ用にカテゴリを2種類に分けて渡す
    success_categories = RecordCategory.objects.filter(user=request.user, type=0)
    regret_categories  = RecordCategory.objects.filter(user=request.user, type=1)

    return render(request, "records/record_form.html", {
        "form": form,
        "saved": saved,
        "return_to_calendar": return_to_calendar,
        "success_categories": success_categories,
        "regret_categories":  regret_categories,
    })
    
    
@login_required
def record_list(request):
    today = date.today()

    # ★ year・month を URL クエリから受け取る（なければ今月）
    try:
        year  = int(request.GET.get("year",  today.year))
        month = int(request.GET.get("month", today.month))
    except ValueError:
        year, month = today.year, today.month

    # 月をまたいでしまったときの補正
    if month > 12:
        year += 1
        month = 1
    elif month < 1:
        year -= 1
        month = 12

    # 前月・次月の year/month を計算（テンプレートのリンク用）
    prev_month = month - 1
    prev_year  = year
    if prev_month < 1:
        prev_month = 12
        prev_year  = year - 1

    next_month = month + 1
    next_year  = year
    if next_month > 12:
        next_month = 1
        next_year  = year + 1

    # カレンダー（週単位の配列）
    cal = calendar.monthcalendar(year, month)

    # 月内の記録を取得
    month_records_qs = (
        Record.objects
        .filter(user=request.user, date__year=year, date__month=month)
        .select_related("category")
        .order_by("date", "created_at")
    )

    # ★ 日付をキーにした辞書に変換
    # 例: {15: [record1, record2], 20: [record3]}
    records_by_day = {}
    for record in month_records_qs:
        day = record.date.day
        if day not in records_by_day:
            records_by_day[day] = []
        records_by_day[day].append(record)

    return render(request, "records/record_list.html", {
        "calendar":      cal,
        "year":          year,
        "month":         month,
        "today":         today,
        "prev_year":     prev_year,
        "prev_month":    prev_month,
        "next_year":     next_year,
        "next_month":    next_month,
        "records_by_day": records_by_day,
    })



#記録の編集   
@login_required
def record_update(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)
    saved = False
    return_to_calendar = False

    if request.method == "POST":
        form = RecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            form = RecordForm(instance=record)
            saved = True
            return_to_calendar = True
    else:
        form = RecordForm(instance=record)

    return render(request, "records/record_form.html", {
        "form": form,
        "saved": saved,
        "return_to_calendar": return_to_calendar,
        "edit_category_type": record.category.type,
        "edit_category_id":   record.category.id,
        "success_categories": RecordCategory.objects.filter(user=request.user, type=0),
        "regret_categories":  RecordCategory.objects.filter(user=request.user, type=1),
    })


#記録の削除
@login_required
def record_delete(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)

    if request.method == "POST":
        record.delete()
        return JsonResponse({"status": "ok"})

    return render(request, "records/record_confirm_delete.html", {"record": record})


# ==============================
# 分析画面（年次・月次）
# ==============================

#年次分析
@login_required
def analysis_year(request):
    year = date.today().year

    qs = (
        Record.objects
        .filter(user=request.user, date__year=year)
        .annotate(month=TruncMonth("date"))
        .values("month", "category__type")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    monthly = {m: {"plus": 0, "minus": 0} for m in range(1, 13)}

    for r in qs:
        m = r["month"].month
        t = r["category__type"]
        total = r["total"] or 0
        if t == 0:
            monthly[m]["plus"] = total
        else:
            monthly[m]["minus"] = total

    labels = list(range(1, 13))
    monthly_net = []
    cumulative_net = []
    running = 0

    for m in labels:
        plus = monthly[m]["plus"]
        minus = monthly[m]["minus"]
        net = plus - minus
        running += net
        monthly_net.append(net)
        cumulative_net.append(running)

    import json
    # アプリ開始からの累計合計
    all_records = Record.objects.filter(user=request.user)
    
    total_ever = all_records.aggregate(
        plus=Sum("amount", filter=models.Q(category__type=0)),
        minus=Sum("amount", filter=models.Q(category__type=1)),
    )
    total_plus  = total_ever["plus"]  or 0
    total_minus = total_ever["minus"] or 0
    total_net   = total_plus - total_minus

    # 最初の記録の年月を取得
    first_record = all_records.order_by("date").first()
    first_label  = f"{first_record.date.year}年{first_record.date.month}月" if first_record else None

    import json
    context = {
        "year": year,
        "labels_json": json.dumps(labels),
        "monthly_net_json": json.dumps(monthly_net),
        "cumulative_net_json": json.dumps(cumulative_net),
        "total_net": total_net,
        "first_label": first_label,
    }

    return render(request, "records/analysis.html", context)


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

    