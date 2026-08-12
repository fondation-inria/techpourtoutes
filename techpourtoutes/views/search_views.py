from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
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
    disambiguate_homonyms: bool = False


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
        disambiguate_homonyms=True,
    ),
    "training_ambassador": SearchScope(
        filters=Q(training_ambassador_eligible=True),
        match_postal_code=False,
        ordering="name",
        row_template="common/partials/school_row/higher_ed.html",
        disambiguate_homonyms=True,
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
    if scope.disambiguate_homonyms:
        _flag_homonyms(items, scope.filters)
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
    """No school means the user could not find hers: offer the whole catalogue."""
    school_id = request.GET.get("school_id", "")
    school = _school_or_none(school_id) if school_id else None
    if school_id and school is None:
        return HttpResponseBadRequest("Établissement inconnu.")

    q, page = _search_params(request)
    formations = Formation.objects.taught_at(school) if school else Formation.objects.all()
    items, next_page = _paginate(formations.search(q).order_by("name"), page)
    return render(
        request,
        "common/partials/formation_results.html",
        {
            "formations": items,
            "q": q,
            "page": page,
            "next_page": next_page,
            "school_id": school.pk if school else "",
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


def _flag_homonyms(schools, filters):
    """Two schools of a same perimeter sharing a name are indistinguishable: say where they are."""
    shared = {
        row["name"]
        for row in School.objects.filter(filters, name__in=[school.name for school in schools])
        .values("name")
        .annotate(count=Count("pk"))
        .filter(count__gt=1)
    }
    for school in schools:
        school.has_homonym = school.name in shared


def _paginate(queryset, page):
    start = (page - 1) * PAGE_SIZE
    items = list(queryset[start : start + PAGE_SIZE + 1])
    next_page = page + 1 if len(items) > PAGE_SIZE else None
    return items[:PAGE_SIZE], next_page
