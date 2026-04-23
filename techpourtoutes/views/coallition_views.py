from django.shortcuts import render  # , get_object_or_404, redirect

# from django.contrib.auth.decorators import user_passes_test, login_required
# from django.utils import timezone
# from ..models import Post, Comment
# from ..forms import PostForm, CommentForm


def coallition_index(request):
    return render(request, "coallition/index.html", {})


def mentor_landing(request):
    return render(request, "coallition/mentor_landing.html", {})
