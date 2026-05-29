from django.contrib import messages
from django.shortcuts import redirect, render

from ..forms import ProForm
from ..services.create_mentor import CreateMentor


def coallition_index(request):
    return render(request, "coallition/index.html", {})


def mentor_landing(request):
    if request.method == "POST":
        form = ProForm(data=request.POST)
        if form.is_valid():
            result = CreateMentor(pro=form.save(commit=False))
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
                return render(request, "coallition/mentor_landing.html", {"form": form})
            return redirect("coallition_welcome")
    else:
        form = ProForm()
    return render(request, "coallition/mentor_landing.html", {"form": form})


def coallition_welcome(request):
    return render(request, "coallition/coallition_welcome.html", {})
