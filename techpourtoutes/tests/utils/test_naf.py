import pytest

from techpourtoutes.utils.naf import naf_label


@pytest.mark.parametrize(
    ("code", "label"),
    [
        ("4321A", "Travaux d'installation électrique dans tous locaux"),
        (
            "0111Z",
            "Culture de céréales (à l'exception du riz), de légumineuses et de graines "
            "oléagineuses",
        ),
        ("9900Z", "Activités des organisations et organismes extraterritoriaux"),
    ],
)
def test_naf_label_is_the_insee_label_of_the_sub_class(code, label):
    assert naf_label(code) == label


@pytest.mark.parametrize("code", ["9999Z", "", None])
def test_naf_label_is_blank_for_a_code_the_nomenclature_does_not_list(code):
    assert naf_label(code) == ""
