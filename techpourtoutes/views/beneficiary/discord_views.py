import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from waffle.decorators import waffle_switch

from ...decorators import beneficiary_required
from ...services.beneficiary.join_discord_server import JoinDiscordServer
from ..beneficiary_views import relay_errors

AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
STATE_SESSION_KEY = "discord_oauth_state"


@waffle_switch("discord")
@beneficiary_required
def new_discord_membership(request):
    request.session[STATE_SESSION_KEY] = state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "response_type": "code",
            "scope": "identify guilds.join",
            "redirect_uri": _redirect_uri(),
            "state": state,
        }
    )
    return redirect(f"{AUTHORIZE_URL}?{query}")


@waffle_switch("discord")
@beneficiary_required
def create_discord_membership(request):
    """Discord's OAuth callback: a GET, since Discord sends her back here with a redirect."""
    if not _state_is_the_one_we_issued(request):
        messages.error(request, "Ce lien a expiré. Recommence depuis le bouton du site.")
        return redirect("show_account")
    if "code" not in request.GET:
        messages.info(request, "Tu n’as pas autorisé Tech pour toutes à t’ajouter au Discord.")
        return redirect("show_account")
    result = JoinDiscordServer(
        beneficiary=request.user.beneficiary,
        code=request.GET["code"],
        redirect_uri=_redirect_uri(),
    )
    if result.failure:
        relay_errors(request, result)
        return redirect("show_account")
    return redirect(f"https://discord.com/channels/{settings.DISCORD_GUILD_ID}")


def _redirect_uri():
    """Discord only sends her back to an address registered in its developer portal."""
    return f"{settings.SITE_URL}{reverse('create_discord_membership')}"


def _state_is_the_one_we_issued(request):
    issued = request.session.pop(STATE_SESSION_KEY, None)
    return issued is not None and secrets.compare_digest(issued, request.GET.get("state", ""))
