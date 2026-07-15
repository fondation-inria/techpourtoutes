from datetime import timedelta

from django.utils import timezone

from techpourtoutes.models import Pro, User, WorkshopRequest

STATS_PERIOD_DAYS = 30


def membres_stats():
    since = timezone.now() - timedelta(days=STATS_PERIOD_DAYS)
    return {
        "total": _stat("Membres", User.objects.all(), since),
        "breakdown": [_stat("Pros", Pro.objects.all(), since)],
    }


def pro_stats():
    since = timezone.now() - timedelta(days=STATS_PERIOD_DAYS)
    return {
        "total": _stat("Pros", Pro.objects.all(), since),
        "breakdown": [
            _stat(
                "Mentors", Pro.objects.filter(engagements__contains=[Pro.Engagement.MENTOR]), since
            ),
            _stat(
                "Ambassadrices étudiantes",
                Pro.objects.filter(engagements__contains=[Pro.Engagement.TRAINING_AMBASSADOR]),
                since,
            ),
            _stat(
                "Proposition de mécénat",
                Pro.objects.filter(engagements__contains=[Pro.Engagement.SPONSOR]),
                since,
            ),
            _stat(
                "Ambassadrices métier",
                Pro.objects.filter(engagements__contains=[Pro.Engagement.WORK_AMBASSADOR]),
                since,
            ),
            _stat("Demandes d'atelier", WorkshopRequest.objects.all(), since),
        ],
    }


def _stat(label, queryset, since):
    return {
        "label": label,
        "total": queryset.count(),
        "recent": queryset.filter(created_at__gte=since).count(),
    }
