from collections.abc import Iterator
from datetime import date, datetime

from defusedxml.ElementTree import iterparse
from django.conf import settings

APEC_SAMPLE_PATH = settings.BASE_DIR / "data" / "apec" / "job_postings_sample.xml"


def read_apec_export_date(file) -> date:
    """The day Apec wrote the export. The file is read to its end all the same, so that an
    export cut short fails here, before a single offer is written."""
    exported_on = None
    for element in _closed_elements(file):
        if element.tag == "Date_export":
            exported_on = datetime.strptime(element.text, "%d/%m/%Y %H:%M:%S").date()
    return exported_on


def read_apec_offers(file) -> Iterator[dict]:
    """Each offer as a dict of its leaf tags, whose names never repeat within an offer
    (`Type_contrat` rather than `Contrat/Type_contrat`), so the sample and the export yield the
    very same dicts."""
    for element in _closed_elements(file):
        if element.tag == "Offre_emploi":
            yield {node.tag: node.text for node in element.iter() if not len(node)}


def _closed_elements(file) -> Iterator:
    """The export weighs some 60 MB: each offer is dropped once handed over, so that memory
    holds one at a time. It never declares a DTD, so one is refused rather than parsed."""
    root = None
    for event, element in iterparse(file, events=("start", "end"), forbid_dtd=True):
        if root is None:
            root = element
        if event == "end":
            yield element
            if element.tag == "Offre_emploi":
                root.clear()
