from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Topic


@login_required
def topic_list(request):
    topics = (
        Topic.objects
        .filter(status=Topic.Status.PUBLIC)
        .select_related("user")
        .order_by("-created_at")
    )
    return render(request, "board/topic_list.html", {"topics": topics})
