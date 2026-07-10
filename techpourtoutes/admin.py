from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils import timezone
from django_otp.admin import OTPAdminSite

from .models import Pro, User, WorkshopRequest

HIDDEN_APP_LABELS = {"auth", "axes", "otp_totp"}
HIDDEN_MODEL_NAMES = {"User"}
STATS_PERIOD_DAYS = 30


class AdminSiteWith2FA(OTPAdminSite):
    # Require a verified TOTP device (2FA) for admin access, except in local development (DEBUG)
    # or when explicitly disabled (DISABLE_ADMIN_2FA, e.g. review apps)
    @property
    def login_form(self):
        return None if self._2fa_disabled() else OTPAdminSite.login_form

    @property
    def login_template(self):
        return None if self._2fa_disabled() else OTPAdminSite.login_template

    def has_permission(self, request):
        if self._2fa_disabled():
            return AdminSite.has_permission(self, request)
        return super().has_permission(request)

    @staticmethod
    def _2fa_disabled():
        return settings.DEBUG or settings.DISABLE_ADMIN_2FA

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)
        app_list = [app for app in app_list if app["app_label"] not in HIDDEN_APP_LABELS]
        for app in app_list:
            app["models"] = [
                model for model in app["models"] if model["object_name"] not in HIDDEN_MODEL_NAMES
            ]
        return app_list

    def app_index(self, request, app_label, extra_context=None):
        if app_label == "techpourtoutes":
            extra_context = {**(extra_context or {}), "stats": _membres_stats()}
        return super().app_index(request, app_label, extra_context)


def _membres_stats():
    since = timezone.now() - timedelta(days=STATS_PERIOD_DAYS)
    return {
        "total": _stat("Membres", User.objects.all(), since),
        "breakdown": [_stat("Pros", Pro.objects.all(), since)],
    }


def _pro_stats():
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


admin.site.__class__ = AdminSiteWith2FA

# Credentials and login-token fields must never be exposed through the admin: a password
# typed here would be stored unhashed
CREDENTIAL_FIELDS = ("password", "login_token_hash")


@admin.register(User)
class AccountAdmin(admin.ModelAdmin):
    exclude = CREDENTIAL_FIELDS


@admin.register(Pro)
class ProAdmin(AccountAdmin):
    exclude = (*CREDENTIAL_FIELDS, "jobirl_user_token")
    readonly_fields = ("jobirl_user_id",)

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "stats": _pro_stats()}
        return super().changelist_view(request, extra_context=extra_context)
