from django.shortcuts import render
from .forms import RecordForm

def record_create(request):
    form = RecordForm()
    return render(request, "records/record_form.html",{"form": form})

