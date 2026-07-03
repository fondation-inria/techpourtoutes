from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django_otp.admin import OTPAdminSite

from .models import Pro, User


class AdminSiteWith2FA(OTPAdminSite):
    # Require a verified TOTP device (2FA) for admin access, except in local development (DEBUG)
    # or when explicitly disabled (DISABLE_ADMIN_2FA, e.g. review apps), where the stock login
    # form and permissions apply so no second factor is needed. Settings are read per request
    # because admin autodiscover runs before the test runner forces DEBUG=False.
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


admin.site.__class__ = AdminSiteWith2FA

# Credentials and login-token fields must never be exposed through the admin: a password
# typed here would be stored unhashed
CREDENTIAL_FIELDS = ("password", "login_token_hash")


@admin.register(User)
class AccountAdmin(admin.ModelAdmin):
    exclude = CREDENTIAL_FIELDS


@admin.register(Pro)
class ProAdmin(AccountAdmin):
    # The Jobirl token is a credential; the Jobirl id is set by the API, so show it read-only.
    exclude = (*CREDENTIAL_FIELDS, "jobirl_user_token")
    readonly_fields = ("jobirl_user_id",)
