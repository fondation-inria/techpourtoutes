import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SVG_SOURCE_DIR = Path(settings.BASE_DIR) / "ui" / "svg_source"
SPRITE_PATH = Path(settings.BASE_DIR) / "ui" / "static" / "svg" / "sprite.svg"

INNER_STROKE_GROUP = re.compile(r'<g class="inner-stroke-shape"[^>]*>')
STROKE_SHAPE = re.compile(r'<\w+\b[^>]*\bid="stroke-shape-[^"]*"[^>]*/>')
STROKE_WIDTH = re.compile(r"stroke-width:\s*([\d.]+)")


def _closing_g(content: str, start: int) -> int:
    depth = 0
    for tag in re.finditer(r"<g\b[^>]*>|</g>", content[start:]):
        depth += -1 if tag.group() == "</g>" else 1
        if depth == 0:
            return start + tag.end()
    raise ValueError("unbalanced <g>")


def _centred_stroke(shape: str) -> str:
    shape = re.sub(r'\s*\bid="stroke-shape-[^"]*"', "", shape)
    return STROKE_WIDTH.sub(lambda width: f"stroke-width: {float(width[1]) / 2:g}", shape)


def _flatten_inner_strokes(content: str) -> str:
    """Penpot draws those at double width and halves them with a clip-path. Firefox and WebKit
    do not resolve that clip-path through an external <use>, which is how the sprite is
    consumed, so they paint the shape at full width — twice as bold as intended.
    """
    parts, cursor = [], 0
    for group in INNER_STROKE_GROUP.finditer(content):
        end = _closing_g(content, group.start())
        shape = STROKE_SHAPE.search(content, group.end(), end)
        parts.append(content[cursor : group.start()])
        parts.append(group.group().replace("inner-stroke-shape", "stroke-shape"))
        parts.append(_centred_stroke(shape.group()))
        parts.append("</g>")
        cursor = end
    parts.append(content[cursor:])
    return "".join(parts)


def _namespace_ids(content: str, slug: str) -> str:
    content = re.sub(r"\bxlink:href=", "href=", content)
    ids = re.findall(r'\bid="([^"]+)"', content)
    for id_val in ids:
        escaped = re.escape(id_val)
        content = re.sub(rf'\bid="{escaped}"', f'id="{slug}-{id_val}"', content)
        content = re.sub(rf"url\(#{escaped}\)", f"url(#{slug}-{id_val})", content)
        content = re.sub(rf"url\('#{escaped}'\)", f"url('#{slug}-{id_val}')", content)
        content = re.sub(rf'href="#{escaped}"', f'href="#{slug}-{id_val}"', content)
        content = re.sub(rf"href='#{escaped}'", f"href='#{slug}-{id_val}'", content)
    return content


class Command(BaseCommand):
    help = "Generate ui/static/svg/sprite.svg from SVG files in ui/svg_source/"

    def handle(self, *args, **options):
        svg_files = sorted(SVG_SOURCE_DIR.rglob("*.svg"))
        if not svg_files:
            self.stderr.write(f"No SVG files found in {SVG_SOURCE_DIR}")
            return

        symbols = []
        for svg_file in svg_files:
            slug = "-".join(svg_file.relative_to(SVG_SOURCE_DIR).with_suffix("").parts)
            content = svg_file.read_text(encoding="utf-8")

            root_match = re.search(r"<svg\b([^>]*?)>(.*?)</svg>", content, re.DOTALL)
            if not root_match:
                self.stderr.write(f"Skipping {svg_file.name}: could not parse SVG")
                continue
            root_attrs = root_match.group(1)
            inner = root_match.group(2).strip()

            viewbox_match = re.search(r'viewBox="([^"]+)"', root_attrs)
            viewbox = viewbox_match.group(1) if viewbox_match else "0 0 24 24"

            # Carry fill from source <svg> into <symbol> so paths inherit it
            fill_match = re.search(r'\bfill="([^"]+)"', root_attrs)
            fill_attr = f' fill="{fill_match.group(1)}"' if fill_match else ""

            inner = _namespace_ids(_flatten_inner_strokes(inner), slug)

            symbols.append(
                f'  <symbol id="{slug}" viewBox="{viewbox}"{fill_attr}>\n    {inner}\n  </symbol>'
            )

        sprite = (
            '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n'
            + "\n".join(symbols)
            + "\n</svg>\n"
        )

        SPRITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SPRITE_PATH.write_text(sprite, encoding="utf-8")
        relative = SPRITE_PATH.relative_to(settings.BASE_DIR)
        self.stdout.write(
            self.style.SUCCESS(f"Sprite generated with {len(symbols)} symbols → {relative}")
        )
