import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

BLANK_LINE = re.compile(r"\n\s*\n")


@register.filter
def paragraphs(value):
    """Wraps each block of text separated by a blank line in a <p>, a single line break in it
    becoming a <br> — as `linebreaks` does, but blind to the indentation of the template."""
    blocks = BLANK_LINE.split(conditional_escape(value))
    lines = ([line.strip() for line in block.split("\n") if line.strip()] for block in blocks)
    return mark_safe("".join(f"<p>{'<br>'.join(block)}</p>" for block in lines if block))
