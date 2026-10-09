from xml.etree import ElementTree

from django.core.management import call_command

from ui.management.commands import build_svg_sprite


def test_sprite_is_well_formed_xml():
    # Firefox drops every icon of an external sprite that fails to parse; Chromium does not.
    ElementTree.parse(build_svg_sprite.SPRITE_PATH)


def test_sprite_matches_build_svg_sprite_output(tmp_path, settings, monkeypatch):
    sprite = build_svg_sprite.SPRITE_PATH.read_text()
    settings.BASE_DIR = tmp_path
    monkeypatch.setattr(build_svg_sprite, "SPRITE_PATH", tmp_path / "sprite.svg")

    call_command("build_svg_sprite")

    assert sprite == (tmp_path / "sprite.svg").read_text()
