from django.db.models import Q
from django.shortcuts import render

from ..models import HigherEdSchool, School
from ..text import strip_accents

SCHOOL_PAGE_SIZE = 20


def search_schools(request):
    q, page = _search_params(request)
    schools = School.objects.all()
    for token in q.split():
        schools = schools.filter(
            Q(name_normalized__icontains=strip_accents(token)) | Q(postal_code__startswith=token)
        )
    items, next_page = _paginate(schools.order_by("identifier"), page)
    return render(
        request,
        "coalition/partials/school_results.html",
        {"schools": items, "q": q, "page": page, "next_page": next_page},
    )


def search_higher_ed_schools(request):
    q, page = _search_params(request)
    schools = HigherEdSchool.objects.all()
    for token in q.split():
        needle = strip_accents(token)
        schools = schools.filter(
            Q(name_normalized__icontains=needle) | Q(full_name_normalized__icontains=needle)
        )
    items, next_page = _paginate(schools.order_by("full_name"), page)
    return render(
        request,
        "coalition/partials/higher_ed_school_results.html",
        {"schools": items, "q": q, "page": page, "next_page": next_page},
    )


# ------------------- private -------------------


def _search_params(request):
    q = request.GET.get("q", "").strip()
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1
    return q, page


def _paginate(queryset, page):
    start = (page - 1) * SCHOOL_PAGE_SIZE
    items = list(queryset[start : start + SCHOOL_PAGE_SIZE + 1])
    next_page = page + 1 if len(items) > SCHOOL_PAGE_SIZE else None
    return items[:SCHOOL_PAGE_SIZE], next_page
