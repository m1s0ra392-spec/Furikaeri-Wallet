import calendar
from datetime import date,datetime
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required 
from .forms import RecordForm
from .models import Record  #record_listで使用

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

    records = Record.objects.filter(user=request.user)
    return render(request, "records/record_list.html", {
        "records": records,
        "calendar": cal,
        "year": year,
        "month": month,
        "selected_date": selected_date,
    })
    
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


@login_required
def record_delete(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)

    if request.method == "POST":
        record.delete()
        return redirect("records:record_list")

    # いったん最小：確認画面テンプレ
    return render(request, "records/record_confirm_delete.html", {"record": record})