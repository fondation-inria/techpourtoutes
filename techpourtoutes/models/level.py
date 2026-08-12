from django.db import models
from django.utils.translation import gettext_lazy as _


class Level(models.TextChoices):
    QUATRIEME = "quatrieme", _("Quatrième")
    TROISIEME = "troisieme", _("Troisième")
    SECONDE = "seconde", _("Seconde")
    PREMIERE = "premiere", _("Première")
    CAP = "cap", _("CAP ou équivalent")
    CAP_PLUS_1 = "cap_plus_1", _("CAP ou équivalent + 1 an")
    TERMINALE = "terminale", _("Terminale")
    BAC_1 = "bac_1", _("Bac +1")
    BAC_2 = "bac_2", _("Bac +2")
    BAC_3 = "bac_3", _("Bac +3")
    BAC_4 = "bac_4", _("Bac +4")
    BAC_5 = "bac_5", _("Bac +5")
    BAC_5_PLUS = "bac_5_plus", _("Au-delà de bac +5")
    BAC_6 = "bac_6", _("Bac +6")
    BAC_7 = "bac_7", _("Bac +7")
    BAC_8 = "bac_8", _("Bac +8")
    BAC_9_PLUS = "bac_9_plus", _("Bac +9 et plus")
