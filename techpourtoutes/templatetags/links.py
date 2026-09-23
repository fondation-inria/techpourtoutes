import re

from django import template
from django.core.validators import DomainNameValidator
from django.template.loader import render_to_string
from django.utils.html import Urlizer
from django.utils.safestring import mark_safe

register = template.Library()

LINK_TEMPLATE = "common/partials/linkified_url.html"

# Django only linkifies the seven historical gTLDs, which is too narrow here — `techpourtoutes.io`
# would stay plain text. Accepting any TLD instead is worse: the missing space in
# "nombreuses.Nous" and the plain French "Mme.Dupont" both become links. Hence a hand-held list.
TLDS = "com|edu|gov|int|mil|net|org|fr|io|eu|biz|info|ai|nl|\
        it|pl|es|uk|ac|de|be|ch|ca|co|re|pm|yt|tf|wf|nc|tech|dev|app|cc"


def _render_link(href, url, external):
    """Renders one `inline_link`, collapsed onto a single line.

    The description goes through `linebreaksbr` downstream, which would turn every newline the
    component is written with — inside the icon, inside the class attribute — into a <br>.
    So the markup is squeezed: runs of whitespace down to one space, then none at all around
    the angle brackets. The only text an anchor holds here is a URL, which carries no
    whitespace of its own, so nothing the user typed is touched.

    `href` and `url` arrive escaped by `Urlizer`, hence marked safe rather than escaped twice.
    """
    context = {"href": mark_safe(href), "url": mark_safe(url), "external": external}
    html = render_to_string(LINK_TEMPLATE, context)
    return re.sub(r"\s*([<>])\s*", r"\1", re.sub(r"\s+", " ", html)).strip()


class _Anchor:
    """Stands in for `Urlizer.url_template`, whose `format()` is the last place a link is still
    seen with its scheme: an external URL opens a new tab, a mailto stays an ordinary link.

    `attrs` only ever carries the `rel="nofollow"` that `nofollow=False` already declines.
    """

    def format(self, *, href, attrs, url):
        return _render_link(href, url, external=not href.startswith("mailto:"))


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
