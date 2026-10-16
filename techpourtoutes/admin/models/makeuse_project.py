from django.contrib import admin

from techpourtoutes.models import MakeuseProject


@admin.register(MakeuseProject)
class MakeuseProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "project_type", "creator_name", "contact_email", "created_at")
    list_display_links = list_display
    search_fields = ("title", "project_type", "creator_name", "contact_email")
    readonly_fields = ("slug", "created_at", "updated_at")
