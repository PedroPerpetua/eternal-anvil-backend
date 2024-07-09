from typing import Any, cast
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from users import models


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer for creating users."""

    class Meta:
        model = models.User
        fields = ("id", "username", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data: Any) -> models.User:
        return models.User.objects.create_user(**validated_data)


class UserWhoamiSerializer(serializers.ModelSerializer):
    """Serializer for retrieving the current user's `USERNAME_FIELD` data (usually username or email)."""

    class Meta:
        model = models.User
        fields = (models.User.USERNAME_FIELD,)


class UserChangePasswordSerializer(serializers.ModelSerializer):
    """Serializer for change password requests."""

    password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    class Meta:
        model = models.User
        fields = ("password", "new_password")


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer to handle user's details."""

    class Meta:
        model = models.User
        # Because more fields can be included in the user, instead exclude all that we know we don't want
        exclude = (
            "id",
            "created_at",
            "updated_at",
            "is_deleted",
            "is_staff",
            "is_active",
            "is_superuser",
            "password",
            "last_login",
            "groups",
            "user_permissions",
            "discord_id",
        )


class DiscordLoginSerializer(serializers.Serializer):
    """
    Serializer for Discord OAuth2 logins. Very similar to the
    `rest_framework_simplejwt.serializers.TokenObtainSerializer`.
    """

    code = serializers.CharField(max_length=255, write_only=True)
    # For DRF Spectacular purposes
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs: dict[str, Any]) -> Any:
        code = attrs.get("code")
        # This should go for our own Discord backend
        user = authenticate(self.context["request"], discord_code=code)
        if not user:
            raise AuthenticationFailed("No active account found with the given credentials", code="no_active_account")
        token = cast(RefreshToken, RefreshToken.for_user(user))
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)  # type: ignore[arg-type] # sender can be None
        return {"refresh": str(token), "access": str(token.access_token)}
