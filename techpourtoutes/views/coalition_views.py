from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from ..forms import ProForm, WorkshopForm
from ..mailers import CoalitionMailer
from ..models import School, WorkshopRequest
from ..services.create_mentor import CreateMentor
from ..tasks import notify_workshop_request_task


def coalition_home(request):
    return render(request, "coalition/coalition_home.html", {})


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


def workshops_landing(request):
    if request.method == "POST":
        form = WorkshopForm(data=request.POST)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.engagements.append("workshops")
            pro.save()
            for atelier in form.cleaned_data["ateliers"]:
                WorkshopRequest.objects.create(
                    pro=pro, type=atelier, remark=form.cleaned_data["remark"]
                )
            notify_workshop_request_task.delay(
                str(pro.pk), form.cleaned_data["ateliers"], form.cleaned_data["remark"]
            )
            CoalitionMailer.welcome(pro=pro, token=pro.issue_login_token())
            return redirect("coalition_welcome")
        else:
            messages.error(
                request,
                "Des erreurs empêchent la validation du formulaire, "
                "merci de les corriger et de réessayer à nouveau.",
            )
    else:
        form = WorkshopForm()
    return render(request, "coalition/workshops_landing.html", {"form": form})


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


def search_schools(request):
    q = request.GET.get("q", "").strip()
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1

    schools = School.objects.all()
    for token in q.split():
        schools = schools.filter(
            Q(name_normalized__icontains=School.normalize(token))
            | Q(postal_code__startswith=token)
        )
    schools = schools.order_by("name")

    SCHOOL_PAGE_SIZE = 20
    start = (page - 1) * SCHOOL_PAGE_SIZE
    items = list(schools[start : start + SCHOOL_PAGE_SIZE + 1])
    next_page = page + 1 if len(items) > SCHOOL_PAGE_SIZE else None

    return render(
        request,
        "coalition/partials/school_results.html",
        {"schools": items[:SCHOOL_PAGE_SIZE], "q": q, "page": page, "next_page": next_page},
    )


def coalition_welcome(request):
    return render(request, "coalition/coalition_welcome.html", {})
