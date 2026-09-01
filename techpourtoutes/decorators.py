from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


def _role_required(role, message):
    """Guards a page reserved to one role.

    Both roles are a one-to-one on `User`, so `hasattr` is the whole test. The page exists for
    everyone, only its audience is restricted: hence a redirect with an explanation rather than
    the `Http404` that guards access to a single record.
    """

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, role):
                messages.error(request, message)
                return redirect(reverse("account"))
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


pro_required = _role_required("pro", "Cette page est réservée aux professionnelles.")
beneficiary_required = _role_required("beneficiary", "Cette page est réservée aux bénéficiaires.")
