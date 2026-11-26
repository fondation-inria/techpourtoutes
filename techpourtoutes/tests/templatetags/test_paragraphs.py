from django.utils.safestring import mark_safe

from techpourtoutes.templatetags.paragraphs import paragraphs


def test_each_block_between_blank_lines_becomes_a_paragraph():
    slot = mark_safe("\n    Premier <b>paragraphe</b>.\n    \n\n    Deuxième\n    ligne.\n")

    assert paragraphs(slot) == "<p>Premier <b>paragraphe</b>.</p><p>Deuxième<br>ligne.</p>"


def test_an_unsafe_string_is_escaped():
    assert paragraphs("<script>") == "<p>&lt;script&gt;</p>"
