from datetime import timedelta

from django.utils import timezone

from techpourtoutes.models import Beneficiary, Formation, Pro, School, User

STATS_PERIOD_DAYS = 30


def users_stats():
    since = timezone.now() - timedelta(days=STATS_PERIOD_DAYS)
    return {
        "total": _stat("Utilisateurs enregistrés", User.objects.all(), since),
        "breakdown": [
            _stat("Bénéficiaires", Beneficiary.objects.all(), since),
            _stat("Pros", Pro.objects.all(), since),
        ],
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
            _stat(
                "Demandes d'atelier",
                Pro.objects.filter(engagements__contains=[Pro.Engagement.WORKSHOPS]),
                since,
            ),
        ],
    }


def school_stats():
    return {"total": _count("Établissements", School.objects.all())}


def formation_stats():
    return {"total": _count("Formations", Formation.objects.all())}


def _stat(label, queryset, since):
    return {
        **_count(label, queryset),
        "recent": queryset.filter(created_at__gte=since).count(),
    }


def _count(label, queryset):
    """A stat without the 30-day delta, which says nothing of data landing through an import."""
    return {"label": label, "total": queryset.count()}
