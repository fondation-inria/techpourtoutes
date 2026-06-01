from django.contrib import messages
from django.shortcuts import redirect, render

from ..forms import ProForm
from ..mailers import CoalitionMailer
from ..services.create_mentor import CreateMentor


def coalition_index(request):
    return render(request, "coalition/index.html", {})


def mentor_landing(request):
    if request.method == "POST":
        form = ProForm(data=request.POST)
        if form.is_valid():
            result = CreateMentor(pro=form.save(commit=False))
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
                return render(request, "coalition/mentor_landing.html", {"form": form})
            return redirect("coalition_welcome")
        else:
            messages.error(
                request,
                "Des erreurs empêchent la validation du formulaire, "
                "merci de les corriger et de réessayer à nouveau.",
            )
    else:
        form = ProForm()
    return render(request, "coalition/mentor_landing.html", {"form": form})


def work_ambassador_landing(request):
    if request.method == "POST":
        form = ProForm(data=request.POST)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.engagements.append("work_ambassador")
            pro.save()
            CoalitionMailer.welcome(pro=pro, token=pro.issue_login_token())
            CoalitionMailer.new_pro(pro=pro, engagement="work_ambassador")
            return redirect("coalition_welcome")
        else:
            messages.error(
                request,
                "Des erreurs empêchent la validation du formulaire, "
                "merci de les corriger et de réessayer à nouveau.",
            )
    else:
        form = ProForm()
    return render(request, "coalition/work_ambassador_landing.html", {"form": form})


def internships_landing(request):
    return render(request, "coalition/internships_landing.html", {})


def sponsor_landing(request):
    if request.method == "POST":
        form = ProForm(data=request.POST)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.engagements.append("sponsor")
            pro.save()
            CoalitionMailer.welcome(pro=pro, token=pro.issue_login_token())
            CoalitionMailer.new_pro(pro=pro, engagement="sponsor")
            return redirect("coalition_welcome")
        else:
            messages.error(
                request,
                "Des erreurs empêchent la validation du formulaire, "
                "merci de les corriger et de réessayer à nouveau.",
            )
    else:
        form = ProForm()
    return render(request, "coalition/sponsor_landing.html", {"form": form})


def coalition_welcome(request):
    return render(request, "coalition/coalition_welcome.html", {})
