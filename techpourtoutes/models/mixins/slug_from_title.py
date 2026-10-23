from itertools import count

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.text import slugify


class SlugFromTitleMixin:
    """A unique `slug` derived from `title` on the first save, `SLUG_FALLBACK` when the title
    slugifies to nothing. The model declares the `slug` field itself."""

    SLUG_FALLBACK = ""

    def save(self, *args, **kwargs):
        """The slug is written once: an indexed URL outlives a corrected title."""
        if self.slug:
            super().save(*args, **kwargs)
            return
        self._save_under_a_free_slug(*args, **kwargs)

    def _save_under_a_free_slug(self, *args, **kwargs):
        base = slugify(self.title)[:240] or self.SLUG_FALLBACK
        for rank in count(1):
            self.slug = base if rank == 1 else f"{base}-{rank}"
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                return
            except IntegrityError, ValidationError:
                if not type(self).objects.filter(slug=self.slug).exists():
                    raise
