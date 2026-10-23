import warnings

from django.conf import Settings
from django.utils.deprecation import RemovedInDjango2028Warning


def test_loading_the_settings_raises_no_deprecation_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error", RemovedInDjango2028Warning)
        Settings("conf.settings")
