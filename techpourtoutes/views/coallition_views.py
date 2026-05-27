from django.contrib import messages
from django.shortcuts import redirect, render

from ..forms import MentorForm
from ..services.create_mentor import CreateMentor


def coallition_index(request):
    return render(request, "coallition/index.html", {})


def mentor_landing(request):
    if request.method == "POST":
        form = MentorForm(data=request.POST)
        if form.is_valid():
            result = CreateMentor(mentor=form.save(commit=False))
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
                return render(request, "coallition/mentor_landing.html", {"form": form})
            return redirect("mentor_success")
    else:
        form = MentorForm()
    return render(request, "coallition/mentor_landing.html", {"form": form})


def mentor_success(request):
    return render(request, "coallition/mentor_success.html", {})
