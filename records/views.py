from django.shortcuts import render, redirect
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
    records = Record.objects.filter(user=request.user)
    return render(request, "records/record_list.html", {
        "records": records
    })