from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import render

from ..models import Formation, School

PAGE_SIZE = 20


@dataclass(frozen=True)
class SearchScope:
    """Everything one autocomplete needs: what it looks in, and how it renders a hit."""

    filters: Q
    match_postal_code: bool
    ordering: str
    row_template: str


SCOPES = {
    "secondary": SearchScope(
        filters=Q(secondary=True),
        match_postal_code=True,
        ordering="name",
        row_template="common/partials/school_row/secondary.html",
    ),
    # Same schools as `secondary`, but the workshop form stores the bare school name —
    # it travels to Brevo and to Latitudes as the structure name.
    "workshop": SearchScope(
        filters=Q(secondary=True),
        match_postal_code=True,
        ordering="name",
        row_template="common/partials/school_row/workshop.html",
    ),
    "higher_ed": SearchScope(
        filters=Q(higher_ed=True),
        match_postal_code=False,
        ordering="name",
        row_template="common/partials/school_row/higher_ed.html",
    ),
    "training_ambassador": SearchScope(
        filters=Q(training_ambassador_eligible=True),
        match_postal_code=False,
        ordering="name",
        row_template="common/partials/school_row/higher_ed.html",
    ),
}


def search_schools(request):
    scope_name = request.GET.get("scope", "")
    scope = SCOPES.get(scope_name)
    if scope is None:
        return HttpResponseBadRequest("Périmètre de recherche inconnu.")

    q, page = _search_params(request)
    schools = School.objects.filter(scope.filters).search(
        q, match_postal_code=scope.match_postal_code
    )
    items, next_page = _paginate(schools.order_by(scope.ordering), page)
    return render(
        request,
        "common/partials/school_results.html",
        {
            "schools": items,
            "q": q,
            "page": page,
            "next_page": next_page,
            "scope": scope_name,
            "row_template": scope.row_template,
            "unique_id": request.GET.get("unique_id", ""),
        },
    )


def search_formations(request):
    school = _school_or_none(request.GET.get("school_id"))
    if school is None:
        return HttpResponseBadRequest("Établissement inconnu.")

    q, page = _search_params(request)
    # Scope first: the fallback answers "nothing is taught here", not "nothing matched".
    formations = Formation.objects.taught_at(school).search(q)
    items, next_page = _paginate(formations.order_by("name"), page)
    return render(
        request,
        "common/partials/formation_results.html",
        {
            "formations": items,
            "q": q,
            "page": page,
            "next_page": next_page,
            "school_id": school.pk,
            "unique_id": request.GET.get("unique_id", ""),
        },
    )


# ------------------- private -------------------


def _school_or_none(school_id):
    try:
        return School.objects.get(pk=school_id)
    except School.DoesNotExist, ValidationError, ValueError:
        return None


def _search_params(request):
    q = request.GET.get("q", "").strip()
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1
    return q, page


def _paginate(queryset, page):
    start = (page - 1) * PAGE_SIZE
    items = list(queryset[start : start + PAGE_SIZE + 1])
    next_page = page + 1 if len(items) > PAGE_SIZE else None
    return items[:PAGE_SIZE], next_page
