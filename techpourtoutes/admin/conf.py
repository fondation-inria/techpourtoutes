from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django_otp.admin import OTPAdminSite

from .stats import users_stats

HIDDEN_APP_LABELS = {"auth", "axes", "otp_totp"}
HIDDEN_MODEL_NAMES = {"User"}


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
            extra_context = {**(extra_context or {}), "stats": users_stats()}
        return super().app_index(request, app_label, extra_context)


admin.site.__class__ = AdminSiteWith2FA
