from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from ..forms import EngagementForm, TrainingAmbassadorForm, WorkshopForm
from ..mailers import CoalitionMailer
from ..models import Pro, School, WorkshopRequest
from ..services.create_mentor import CreateMentor
from ..tasks import notify_workshop_request_task


def coalition_home(request):
    return render(request, "coalition/coalition_home.html", {})


def mentor_landing(request):
    pro = _current_pro(request)
    if request.method == "POST":
        form = EngagementForm(data=request.POST, pro=pro)
        if form.is_valid():
            result = CreateMentor(pro=form.save(commit=False))
            if result.failure:
                for error in result.errors:
                    messages.error(request, error)
                return render(request, "coalition/mentor_landing.html", {"form": form, "pro": pro})
            return redirect("coalition_welcome")
        else:
            _render_errors(request, form)
    else:
        form = EngagementForm(pro=pro)
    return render(request, "coalition/mentor_landing.html", {"form": form, "pro": pro})


def work_ambassador_landing(request):
    return _handle_engagement(
        request,
        form_class=EngagementForm,
        engagement=Pro.Engagement.WORK_AMBASSADOR,
        template="coalition/work_ambassador_landing.html",
    )


def training_ambassador_landing(request):
    return _handle_engagement(
        request,
        form_class=TrainingAmbassadorForm,
        engagement=Pro.Engagement.TRAINING_AMBASSADOR,
        template="coalition/training_ambassador_landing.html",
    )


def sponsor_landing(request):
    return _handle_engagement(
        request,
        form_class=EngagementForm,
        engagement=Pro.Engagement.SPONSOR,
        template="coalition/sponsor_landing.html",
    )


def internships_landing(request):
    return render(request, "coalition/internships_landing.html", {})


def workshops_landing(request):
    pro = _current_pro(request)
    if request.method == "POST":
        form = WorkshopForm(data=request.POST, pro=pro)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.add_engagement(Pro.Engagement.WORKSHOPS)
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
            _render_errors(request, form)
    else:
        form = WorkshopForm(pro=pro)
    return render(request, "coalition/workshops_landing.html", {"form": form, "pro": pro})


def coalition_welcome(request):
    return render(request, "coalition/coalition_welcome.html", {})


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
    schools = schools.order_by("identifier")

    SCHOOL_PAGE_SIZE = 20
    start = (page - 1) * SCHOOL_PAGE_SIZE
    items = list(schools[start : start + SCHOOL_PAGE_SIZE + 1])
    next_page = page + 1 if len(items) > SCHOOL_PAGE_SIZE else None

    return render(
        request,
        "coalition/partials/school_results.html",
        {"schools": items[:SCHOOL_PAGE_SIZE], "q": q, "page": page, "next_page": next_page},
    )


# ------------------- private -------------------


def _current_pro(request):
    return request.user.pro if hasattr(request.user, "pro") else None


def _handle_engagement(request, *, form_class, engagement, template):
    pro = _current_pro(request)
    if request.method == "POST":
        form = form_class(data=request.POST, pro=pro)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.add_engagement(engagement)
            pro.save()
            CoalitionMailer.welcome(pro=pro, token=pro.issue_login_token())
            CoalitionMailer.new_pro(pro=pro, engagement=engagement)
            return redirect("coalition_welcome")
        else:
            _render_errors(request, form)
    else:
        form = form_class(pro=pro)
    return render(request, template, {"form": form, "pro": pro})


def _render_errors(request, form):
    if form.has_error("email", "email_exists"):
        messages.error(
            request,
            "Un compte existe déjà pour cet email, merci de vous connecter "
            "avant de soumettre votre engagement.",
        )
    else:
        messages.error(
            request,
            "Des erreurs empêchent la validation du formulaire, "
            "merci de les corriger et de réessayer à nouveau.",
        )
