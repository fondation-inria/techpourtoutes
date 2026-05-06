from django.contrib import messages
from django.shortcuts import redirect, render

from api.services.jobirl_api.register_mentor import RegisterMentorOnJobirl

from ..forms import MentorForm
from ..mailers import MentorMailer


def coallition_index(request):
    return render(request, "coallition/index.html", {})


def mentor_landing(request):
    if request.method == "POST":
        form = MentorForm(data=request.POST)
        if form.is_valid():
            mentor = form.save(commit=False)
            result = RegisterMentorOnJobirl(mentor=mentor)
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
                return render(request, "coallition/mentor_landing.html", {"form": form})
            mentor.jobirl_user_id, mentor.jobirl_user_token = result.user_id, result.token
            mentor.save()
            MentorMailer.welcome(mentor)
            return redirect("mentor_success")
    else:
        form = MentorForm()
    return render(request, "coallition/mentor_landing.html", {"form": form})


def mentor_success(request):
    return render(request, "coallition/mentor_success.html", {})
