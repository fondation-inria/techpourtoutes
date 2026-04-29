from django.shortcuts import redirect, render

from ..forms import MentorForm


def coallition_index(request):
    return render(request, "coallition/index.html", {})


def mentor_landing(request):
    if request.method == "POST":
        form = MentorForm(data=request.POST)
        if form.is_valid():
            form.save()
            return redirect("mentor_success")
    else:
        form = MentorForm()
    return render(request, "coallition/mentor_landing.html", {"form": form})


def mentor_success(request):
    return render(request, "coallition/mentor_success.html", {})
