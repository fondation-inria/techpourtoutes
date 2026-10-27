from django.contrib.staticfiles import finders
from django.utils import timezone
from fpdf import FPDF
from fpdf.enums import Align, XPos, YPos

_LOGO = "images/techpourtoutes-logo-new-beneficiary.png"
_GREY = (107, 114, 128)


def build_authorization_proof(authorization):
    """The PDF mailed to the signatory, and kept as is: the text signed and when it was.

    It lays out `authorization.document` itself, so it shows exactly what was signed: blocks
    separated by a blank line — the title, the paragraphs, the `Label : value` identity lines,
    then the `[x]` statements. The rest of the proof (IP) stays in the database."""
    title, *paragraphs, identity, statements = authorization.document.split("\n\n")
    pdf = _new_pdf()
    pdf.image(finders.find(_LOGO), w=45)
    pdf.ln(8)
    _title(pdf, title)
    for paragraph in paragraphs:
        _paragraph(pdf, paragraph)
    for line in identity.splitlines():
        _field(pdf, *line.split(" : ", 1))
    pdf.ln(3)
    for line in statements.splitlines():
        _checkbox(pdf, line[4:], checked=line.startswith("[x]"))
    _signature(pdf, authorization.signed_at)
    return bytes(pdf.output())


def _new_pdf():
    pdf = FPDF()
    pdf.add_font("Poppins", "", finders.find("fonts/poppins/poppins-latin-400-normal.woff2"))
    pdf.add_font("Poppins", "B", finders.find("fonts/poppins/poppins-latin-600-normal.woff2"))
    pdf.add_font(
        "Newsreader", "BI", finders.find("fonts/newsreader/newsreader-latin-800-italic.woff2")
    )
    pdf.set_margins(20, 20)
    pdf.add_page()
    return pdf


def _lines(pdf, height, text):
    pdf.multi_cell(0, height, text, align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _title(pdf, text):
    pdf.set_font("Newsreader", "BI", 20)
    _lines(pdf, 9, text)
    pdf.ln(4)


def _paragraph(pdf, text):
    pdf.set_font("Poppins", "", 10)
    _lines(pdf, 5, text)
    pdf.ln(3)


def _field(pdf, label, value):
    pdf.set_font("Poppins", "B", 10)
    pdf.cell(h=6, text=f"{label} : ")
    pdf.set_font("Poppins", "", 10)
    _lines(pdf, 6, value)


def _checkbox(pdf, text, *, checked):
    x, y = pdf.get_x(), pdf.get_y()
    pdf.rect(x, y + 0.5, 4, 4)
    if checked:
        pdf.set_line_width(0.4)
        pdf.line(x + 0.8, y + 2.6, x + 1.7, y + 3.6)
        pdf.line(x + 1.7, y + 3.6, x + 3.3, y + 1.3)
        pdf.set_line_width(0.2)
    pdf.set_x(x + 7)
    pdf.set_font("Poppins", "", 9)
    _lines(pdf, 5, text)
    pdf.ln(2)


def _signature(pdf, signed_at):
    pdf.ln(6)
    pdf.set_font("Poppins", "", 9)
    pdf.set_text_color(*_GREY)
    _lines(
        pdf,
        5,
        f"Signée en ligne le {timezone.localtime(signed_at):%d/%m/%Y à %H:%M} (heure de Paris).",
    )
    pdf.set_text_color(0)
