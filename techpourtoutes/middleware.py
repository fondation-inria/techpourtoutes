from waffle import switch_is_active


class SiteModeUrlconfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            is_beneficiary = switch_is_active("beneficiary_mode")
        except Exception:
            is_beneficiary = False
        request.site_mode = "beneficiary" if is_beneficiary else "coalition"
        if request.site_mode == "beneficiary":
            request.urlconf = "conf.urls_beneficiary"
        return self.get_response(request)
