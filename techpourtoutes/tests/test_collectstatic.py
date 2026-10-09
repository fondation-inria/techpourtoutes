from django.core.management import call_command


def test_collectstatic_succeeds_with_the_production_storage(settings, tmp_path):
    """The manifest storage follows every reference a CSS or JS file makes, source maps
    included: one pointing at a file we do not ship fails the deploy."""
    settings.STATIC_ROOT = tmp_path
    settings.STORAGES = settings.STORAGES | {
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
    }

    call_command("collectstatic", "--noinput", verbosity=0)
