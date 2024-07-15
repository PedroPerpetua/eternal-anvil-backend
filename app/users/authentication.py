from typing import Any, Optional, cast
import requests
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.http.request import HttpRequest
from rest_framework.permissions import IsAuthenticated as BaseIsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView
from users.models import User


class AuthenticationBackend(ModelBackend):
    """Custom authentication backend that also checks for the `is_deleted` status."""

    def user_can_authenticate(self, user: Optional[AbstractBaseUser | AnonymousUser]) -> bool:
        """Override this method so that we can check for the `is_deleted` status."""
        if not user:  # pragma: no cover
            return False
        is_deleted = getattr(user, "is_deleted", False)
        if is_deleted:
            return False
        return super().user_can_authenticate(user)


class AuthenticatedRequest(Request):
    """Authenticated class to correctly type the user in requests."""

    user: User


class IsAuthenticated(BaseIsAuthenticated):
    """Modify the IsAuthenticated permission to block inactive and deleted users."""

    def has_permission(self, request: AuthenticatedRequest, view: APIView) -> bool:  # type: ignore[override]
        return super().has_permission(request, view) and request.user.is_active and not request.user.is_deleted


class IsStaff(IsAuthenticated):
    """Extend the `IsAuthenticated` permission to only allow users with `is_staff == True`."""

    def has_permission(self, request: AuthenticatedRequest, view: APIView) -> bool:  # type: ignore[override]
        return super().has_permission(request, view) and request.user.is_staff


class DiscordAuthenticationBackend(AuthenticationBackend):
    """Custom authentication backend for Discord OAuth2."""

    def get_discord_data(self, access_token: str) -> Optional[tuple[str, str]]:
        """Retrieve the account's Id and username, from the exchanged access token."""
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.get("https://discordapp.com/api/users/@me", headers=headers)
        if not res.ok:
            return None
        data: dict[str, str] = res.json()
        discord_id = data.get("id")
        username = data.get("username")
        if not discord_id or not username:
            return None
        return (discord_id, username)

    def exchange_discord_code(self, discord_code: str) -> Optional[str]:
        """Exchange the Discord OAuth2 code from the Authorization step for a Discord Access Token."""
        payload = {
            "grant_type": "authorization_code",
            "code": discord_code,
            "redirect_uri": settings.DISCORD_REDIRECT_URL,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        res = requests.post(
            "https://discord.com/api/oauth2/token",
            data=payload,
            headers=headers,
            auth=(settings.DISCORD_CLIENT_ID, settings.DISCORD_CLIENT_SECRET),
        )
        if not res.ok:
            return None
        return cast(str, res.json()["access_token"])

    def authenticate(  # type: ignore[override] # We want our backend to have a different signature
        self, request: Optional[HttpRequest], discord_code: Optional[str] = None, **kwargs: Any
    ) -> Optional[AbstractBaseUser]:
        """
        Authenticate the user into our system using the OAuth2 Discord Code obtained from the Authorization step.
        """
        if not discord_code:
            return None
        access_code = self.exchange_discord_code(discord_code)
        if access_code is None:
            return None
        user_data = self.get_discord_data(access_code)
        if user_data is None:
            return None
        discord_id, discord_username = user_data
        user = User.get_user_for_discord_id(discord_id, discord_username)
        if not self.user_can_authenticate(user):
            return None
        return user
