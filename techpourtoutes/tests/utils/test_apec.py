from datetime import date
from io import BytesIO

from techpourtoutes.utils.apec import APEC_SAMPLE_PATH, read_apec_xml

EXPORT = b"""<?xml version='1.0' encoding='UTF-8'?>
<Export_offres>
  <Export>
    <Partenaire>TECHPOURTOUTES</Partenaire>
    <Date_export>02/11/2026 01:46:47</Date_export>
  </Export>
  <Offre_emploi>
    <Reference_apec>179254673W</Reference_apec>
    <Intitule><![CDATA[D\xc3\xa9veloppeur BI F/H]]></Intitule>
    <Contrat>
      <Type_contrat>CDD</Type_contrat>
      <Duree_contrat>12</Duree_contrat>
    </Contrat>
    <Texte_offre><![CDATA[<p>D&eacute;veloppeur BI</p>]]></Texte_offre>
  </Offre_emploi>
  <Offre_emploi>
    <Reference_apec>179334000W</Reference_apec>
    <Contrat>
      <Type_contrat>CDI</Type_contrat>
    </Contrat>
  </Offre_emploi>
</Export_offres>
"""


def test_the_day_apec_wrote_the_export_is_read():
    exported_on, _ = read_apec_xml(BytesIO(EXPORT))

    assert exported_on == date(2026, 11, 2)


def test_every_offer_is_read_keyed_by_its_tags_out_of_their_cdata():
    _, (first, second) = read_apec_xml(BytesIO(EXPORT))

    assert first == {
        "Reference_apec": "179254673W",
        "Intitule": "Développeur BI F/H",
        "Type_contrat": "CDD",
        "Duree_contrat": "12",
        "Texte_offre": "<p>D&eacute;veloppeur BI</p>",
    }
    assert second == {"Reference_apec": "179334000W", "Type_contrat": "CDI"}


def test_the_committed_sample_is_an_export_like_the_others():
    _, records = read_apec_xml(APEC_SAMPLE_PATH)

    assert len(records) == 40
    assert all(record["Reference_apec"] for record in records)
