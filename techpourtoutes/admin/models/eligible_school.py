from django.contrib import admin

from techpourtoutes.models import EligibleSchool


@admin.register(EligibleSchool)
class EligibleSchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "postal_code", "education_level", "matches_digital_domain")
    list_display_links = list_display
    search_fields = ("name",)
    list_filter = ("education_level", "matches_digital_domain")
