from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.views.decorators.http import require_POST

from ...forms import (
    ProAdditionalInformationForm,
    ProTrainingAmbassadorForm,
    ProWorkshopRequestForm,
)
from ...models import Pro
from ...services.pro.add_pro_engagement import AddProEngagement
from ...utils.pro_engagement_screens import screen_for

_ADDED = "Votre engagement a bien été ajouté."


# A visitor signs up with the engagement; a pro completes, on one screen, what it still needs.
def new_pro_engagement(request, engagement):
    _require_engagement(engagement)
    if not request.user.is_authenticated:
        query = urlencode({"engagement": engagement})
        return redirect(f"{reverse('new_pro_inscription_funnel')}?{query}")
    pro = _current_pro(request)
    step = screen_for(pro, engagement)
    if step is None:
        return redirect("show_account")
    origin = _origin_page(request, request.headers.get("Referer"))
    return render(
        request,
        "coalition/funnels/new_pro_engagement.html",
        _step_context(engagement, step, _form(step, pro), origin),
    )


@login_required
@require_POST
def create_pro_engagement(request, engagement):
    _require_engagement(engagement)
    pro = _current_pro(request)
    origin = _origin_page(request, request.GET.get("next"))
    step = screen_for(pro, engagement)
    form = _form(step, pro, request.POST)
    if form is not None and not form.is_valid():
        context = _step_context(engagement, step, form, origin)
        return render(request, context["step_template"], context)

    result = AddProEngagement(pro=pro, engagement=engagement, **_screen_answers(step, form))
    if result.failure:
        url = origin or reverse("show_account")
        return _go_to(request, url, messages.ERROR, ", ".join(result.errors))
    return _go_to(request, reverse("show_account"), messages.SUCCESS, _ADDED)


# ------------------- private -------------------


def _require_engagement(engagement):
    if engagement not in Pro.Engagement.values:
        raise Http404


def _current_pro(request):
    if not hasattr(request.user, "pro"):
        raise Http404
    return request.user.pro


# Only a page of the site: anything else would make an open redirect.
def _origin_page(request, url):
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return None


def _form(step, pro, data=None):
    if step == "training_ambassador":
        return ProTrainingAmbassadorForm(data=data)
    if step == "workshop_request":
        return ProWorkshopRequestForm(data=data)
    if step == "additional_information":
        return ProAdditionalInformationForm(data=data, pro=pro)
    return None


def _screen_answers(step, form):
    if step == "training_ambassador":
        return {"training_ambassador_form": form}
    if step == "workshop_request":
        return {"workshop_request_form": form}
    if step == "additional_information":
        return {"additional_information": form.cleaned_data}
    return {}


def _step_context(engagement, step, form, origin):
    funnel_url = reverse("create_pro_engagement", args=[engagement])
    return {
        "step": step,
        "step_template": f"coalition/funnels/partials/pro_inscription/steps/{step}.html",
        "form": form,
        "funnel_url": f"{funnel_url}?{urlencode({'next': origin})}" if origin else funnel_url,
        "back_url": origin or reverse("show_account"),
        "submit_label": "Valider",
    }


def _go_to(request, url, level, message):
    messages.add_message(request, level, message)
    return HttpResponse(headers={"HX-Redirect": url})
