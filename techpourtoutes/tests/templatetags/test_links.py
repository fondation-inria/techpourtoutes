import pytest

from techpourtoutes.templatetags.links import linkify

# The five forms a user may type, and the href each one should point at. The label is never
# rewritten: she reads back exactly what she wrote.
WRITTEN_AS = [
    ("techpourtoutes.io", "https://techpourtoutes.io"),
    ("www.techpourtoutes.io", "https://www.techpourtoutes.io"),
    ("http://techpourtoutes.io", "http://techpourtoutes.io"),
    ("http://www.techpourtoutes.io", "http://www.techpourtoutes.io"),
    ("https://www.techpourtoutes.io", "https://www.techpourtoutes.io"),
]

# An oubli d'espace after a full stop is common, and "M.Dupont" is plain French: none of these
# is a link. They are the reason the accepted TLDs are an explicit list.
PROSE = [
    "Venez nombreuses.Nous vous attendons à 18h",
    "Animé par M.Dupont et Mme.Martin",
    "Atelier de 14h à 18h.Fin de la journée à 20h",
    "Plus d'infos etc.Voir le programme complet",
    "Tarif 3.50 euros",
]


@pytest.mark.parametrize("written,href", WRITTEN_AS)
def test_linkify_keeps_the_url_as_it_was_written(written, href):
    assert f'href="{href}"' in linkify(written)
    assert f">{written}<" in linkify(written)


def test_linkify_opens_external_links_in_a_new_tab_with_an_icon():
    html = linkify("Infos sur https://techpourtoutes.io")

    assert 'target="_blank"' in html
    assert 'rel="nofollow noopener noreferrer"' in html
    assert "#external-link" in html
    # A single `rel`: a second one would be ignored and `noopener` lost with it.
    assert html.count("rel=") == 1


def test_linkify_leaves_an_email_a_plain_mailto():
    html = linkify("Écris à contact@techpourtoutes.io")

    assert 'href="mailto:contact@techpourtoutes.io"' in html
    assert "target=" not in html
    assert "#external-link" not in html


@pytest.mark.parametrize(
    "scheme",
    ["javascript:alert(1)", "data:text/html,<b>x</b>", "vbscript:msgbox(1)"],
)
def test_linkify_never_builds_a_link_out_of_a_dangerous_scheme(scheme):
    assert "<a" not in linkify(f"Voir {scheme} ici")


def test_linkify_escapes_the_text_around_the_links():
    html = linkify("<img src=x onerror=alert(1)> puis https://techpourtoutes.io")

    assert "<img" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_linkify_escapes_a_url_that_carries_markup():
    html = linkify('https://techpourtoutes.io/"><script>alert(1)</script>')

    assert "<script>" not in html
    # The quote ends the URL instead of closing the href: what follows is text, and escaped.
    assert html.endswith("&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;")


@pytest.mark.parametrize("text", PROSE)
def test_linkify_leaves_french_prose_alone(text):
    assert "<a" not in linkify(text)


def test_linkify_preserves_the_newlines_the_description_was_typed_with():
    """`linebreaksbr` turns them into <br> downstream, so they have to survive this filter."""
    assert linkify("Première ligne\nhttps://techpourtoutes.io").startswith("Première ligne\n<a ")
