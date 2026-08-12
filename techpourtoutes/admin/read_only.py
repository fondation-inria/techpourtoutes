from django.contrib import admin


class ReadOnlyAdminMixin:
    """Data owned by the Onisep import: displayed in the admin, never edited by hand."""

    def has_add_permission(self, _request):
        return False

    def has_change_permission(self, _request, _obj=None):
        return False

    def has_delete_permission(self, _request, _obj=None):
        return False


class ReadOnlyTabularInline(admin.TabularInline):
    """Related records listed as plain rows — columns only, no per-row object label."""

    extra = 0
    can_delete = False

    class Media:
        css = {"all": ("css/admin_inlines.css",)}

    def has_add_permission(self, _request, _obj=None):
        return False
