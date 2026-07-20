from waffle import switch_is_active


class SiteModeUrlconfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if switch_is_active("beneficiary_mode"):
            request.urlconf = "conf.urls_beneficiary"
        return self.get_response(request)
