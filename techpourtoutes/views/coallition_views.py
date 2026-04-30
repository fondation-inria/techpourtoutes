from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from api.services.jobirl import JobirlAPIError, register_mentor_on_jobirl

from ..forms import MentorForm
from ..mailers import MentorMailer


def coallition_index(request):
    return render(request, "coallition/index.html", {})


def mentor_landing(request):
    if request.method == "POST":
        form = MentorForm(data=request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    mentor = form.save()
                    register_mentor_on_jobirl(mentor)
            except JobirlAPIError as exc:
                messages.error(request, str(exc))
                return render(request, "coallition/mentor_landing.html", {"form": form})
            MentorMailer.welcome(mentor)
            return redirect("mentor_success")
    else:
        form = MentorForm()
    return render(request, "coallition/mentor_landing.html", {"form": form})


def mentor_success(request):
    return render(request, "coallition/mentor_success.html", {})
