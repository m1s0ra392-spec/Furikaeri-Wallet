from django.shortcuts import render

def record_create(request):
    return render(request, "records/record_form.html")

