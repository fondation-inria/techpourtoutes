from django import forms
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from techpourtoutes.forms.event.details_form import (
    IMAGE_CONTENT_TYPES,
    IMAGE_MAX_SIZE,
    IMAGE_SOURCE_MAX_SIZE,
)
from techpourtoutes.forms.fields import UploadedImageKeyField
from techpourtoutes.models import MakeuseProject
from techpourtoutes.models.makeuse_project import IMAGE_PREFIX
from techpourtoutes.services.storage.create_presigned_upload import CreatePresignedUpload

from ..fields import ImageUploadWidget


class MakeuseProjectAdminForm(forms.ModelForm):
    image = UploadedImageKeyField(
        prefix=IMAGE_PREFIX,
        label=_("Visuel"),
        widget=ImageUploadWidget(
            upload_url=reverse_lazy("admin:makeuse_project_image_upload"),
            accept=IMAGE_CONTENT_TYPES,
            source_max_size=IMAGE_SOURCE_MAX_SIZE,
        ),
    )

    class Meta:
        model = MakeuseProject
        fields = (
            "beneficiary",
            "title",
            "category",
            "project_type",
            "creator_name",
            "contact_email",
            "idea",
            "background",
            "methodology",
            "hobbies",
            "image",
            "demo_url",
        )


@admin.register(MakeuseProject)
class MakeuseProjectAdmin(admin.ModelAdmin):
    form = MakeuseProjectAdminForm
    autocomplete_fields = ("beneficiary",)
    list_display = (
        "title",
        "category",
        "project_type",
        "creator_label",
        "contact_label",
        "created_at",
    )
    list_display_links = list_display
    list_filter = ("category",)
    search_fields = ("title", "project_type", "creator_name", "contact_email")
    readonly_fields = ("slug", "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("beneficiary")

    @admin.display(description=_("créatrice"))
    def creator_label(self, obj):
        return obj.creator_label

    @admin.display(description=_("contact"))
    def contact_label(self, obj):
        return obj.contact_label

    def get_urls(self):
        return [
            path(
                "visuel/",
                self.admin_site.admin_view(require_POST(self.create_image_upload)),
                name="makeuse_project_image_upload",
            ),
            *super().get_urls(),
        ]

    def create_image_upload(self, request):
        """Signs the PUT the change form sends its visual with, straight to the bucket."""
        content_length = request.POST.get("content_length", "")
        result = CreatePresignedUpload(
            storage_alias="public",
            prefix=IMAGE_PREFIX,
            content_type=request.POST.get("content_type", ""),
            content_length=int(content_length) if content_length.isdigit() else 0,
            allowed_content_types=IMAGE_CONTENT_TYPES,
            max_size=IMAGE_MAX_SIZE,
        )
        if result.failure:
            return JsonResponse({"error": result.errors[0]}, status=400)
        return JsonResponse({"url": result.url, "headers": result.headers, "key": result.key})
