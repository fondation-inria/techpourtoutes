import re

from django import template
from django.core.validators import DomainNameValidator
from django.template.loader import render_to_string
from django.utils.html import Urlizer
from django.utils.safestring import mark_safe

register = template.Library()

ICON_TEMPLATE = "common/partials/external_link_icon.html"

# Django only linkifies the seven historical gTLDs, which is too narrow here — `techpourtoutes.io`
# would stay plain text. Accepting any TLD instead is worse: the missing space in
# "nombreuses.Nous" and the plain French "Mme.Dupont" both become links. Hence a hand-held list.
TLDS = "com|edu|gov|int|mil|net|org|fr|io|eu|biz|info|ai|nl|\
        it|pl|es|uk|ac|de|be|ch|ca|co|re|pm|yt|tf|wf|nc|tech|dev|app|cc"


class _Anchor:
    """Stands in for `Urlizer.url_template`, whose `format()` is the last place a link is still
    seen with its scheme: an external URL opens a new tab, a mailto stays an ordinary link.

    `href` and `url` arrive escaped by `Urlizer`, so both are interpolated as they are. `attrs`
    only ever carries the `rel="nofollow"` that `nofollow=False` already declines.
    """

    def format(self, *, href, attrs, url):
        if href.startswith("mailto:"):
            return f'<a href="{href}">{url}</a>'
        return (
            f'<a href="{href}" target="_blank" rel="nofollow noopener noreferrer">'
            f"{url}{render_to_string(ICON_TEMPLATE).strip()}</a>"
        )


class _DescriptionUrlizer(Urlizer):
    url_template = _Anchor()
    simple_url_2_re = re.compile(
        rf"^www\.|^(?!http)(?:{DomainNameValidator.hostname_re})"
        rf"(?:{DomainNameValidator.domain_re})"
        rf"\.({TLDS})($|/.*)$",
        re.IGNORECASE,
    )


_urlize = _DescriptionUrlizer()


@register.filter(is_safe=True, needs_autoescape=True)
def linkify(text, autoescape=True):
    """Turns the links a user typed into clickable ones, and escapes everything else.

    `nofollow=False` because the whole `rel` is written by `_Anchor`: a second one would be
    ignored by the browser, and `noopener` lost with it.
    """
    return mark_safe(_urlize(text, nofollow=False, autoescape=autoescape))
