from django.utils.translation import gettext_lazy as _

from ...models import Pro, School

_SCHOOLS_BY_STRUCTURE_TYPE = {
    Pro.StructureType.SCHOOL: School.objects.secondary,
    Pro.StructureType.HIGHER_ED: School.objects.higher_ed,
}


class StructureFormMixin:
    """Names the structure of a pro. A school or a higher-ed establishment is picked in the
    catalogue, whose name is then the one saved, unless hers is missing from it or she keeps the
    one she already has — a structure saved before the catalogue, or since: nothing ties it to a
    school. The form declares `structure_type`, `structure_name` and the hidden fields of the
    search: `structure_school_search_id`, `structure_school_not_found`.

    `structure_school` is only cleaned when the form names the structure: the school picked, or
    none. A structure she keeps, or one the form does not ask, keeps the school it had.
    """

    saved_structure = None

    def clean_structure(self, cleaned_data):
        school_id = cleaned_data.pop("structure_school_search_id", "")
        school_not_found = cleaned_data.pop("structure_school_not_found", False)
        structure_type = cleaned_data.get("structure_type")
        if self._names_the_structure(cleaned_data):
            cleaned_data["structure_school"] = None
        if structure_type in Pro.WITHOUT_STRUCTURE:
            cleaned_data["structure_name"] = ""
        elif self._picks_a_school(cleaned_data, school_not_found):
            self._name_the_picked_school(_SCHOOLS_BY_STRUCTURE_TYPE[structure_type](), school_id)
        elif structure_type and not cleaned_data.get("structure_name"):
            self.add_error("structure_name", _("Ce champ est obligatoire."))

    def _names_the_structure(self, cleaned_data):
        structure = (cleaned_data.get("structure_type"), cleaned_data.get("structure_name"))
        return "structure_name" in self.fields and structure != self.saved_structure

    def _picks_a_school(self, cleaned_data, school_not_found):
        return (
            self._names_the_structure(cleaned_data)
            and cleaned_data.get("structure_type") in _SCHOOLS_BY_STRUCTURE_TYPE
            and not school_not_found
        )

    def _name_the_picked_school(self, schools, school_id):
        """The name is the catalogue's, not the label the search displayed."""
        school = schools.find(school_id) if school_id else None
        if school is None:
            self.add_error("structure_name", _("Sélectionnez un établissement dans la liste."))
        else:
            self.cleaned_data["structure_name"] = school.name
            self.cleaned_data["structure_school"] = school
