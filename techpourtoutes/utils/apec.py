from datetime import date, datetime

from defusedxml.ElementTree import iterparse
from django.conf import settings

APEC_SAMPLE_PATH = settings.BASE_DIR / "data" / "apec" / "job_postings_sample.xml"


def read_apec_xml(file) -> tuple[date, list[dict]]:
    """The day Apec wrote the export, and each offer as a dict of its leaf tags, whose names
    never repeat within an offer (`Type_contrat` rather than `Contrat/Type_contrat`), so the
    sample and the export yield the very same dicts.

    The export weighs some 60 MB: it is read one offer at a time. It never declares a DTD, so
    one is refused rather than parsed.
    """
    exported_on, records = None, []
    for _, element in iterparse(file, forbid_dtd=True):
        if element.tag == "Date_export":
            exported_on = datetime.strptime(element.text, "%d/%m/%Y %H:%M:%S").date()
        elif element.tag == "Offre_emploi":
            records.append({node.tag: node.text for node in element.iter() if not len(node)})
            element.clear()
    return exported_on, records
