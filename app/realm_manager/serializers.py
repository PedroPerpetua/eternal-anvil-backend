from typing import Any, Literal, Optional
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from drf_spectacular.openapi import AutoSchema, OpenApiSerializerExtension
from extensions.serializers import NestedPrimaryKeyRelatedField
from realm_manager import models
from users.models import User


# GameWorlds -----------------------------------------------------------------


class ListGameWorld(serializers.ModelSerializer[models.GameWorld]):
    account_name = serializers.SerializerMethodField()

    class Meta:
        model = models.GameWorld
        fields = ("id", "name", "code", "start", "end", "account_name")

    def get_account_name(self, instance: models.GameWorld) -> Optional[str]:
        user: User = self.context["request"].user
        account = instance.accounts.filter(players__user=user).first()
        if not account:
            return None
        return account.name


# Accounts -------------------------------------------------------------------
class GameWorldSerializer(serializers.ModelSerializer[models.GameWorld]):
    class Meta:
        model = models.GameWorld
        fields = ("id", "name", "code")


class UserSerializer(serializers.ModelSerializer[models.User]):
    class Meta:
        model = User
        fields = ("id", "username")


class RealmSerializer(serializers.ModelSerializer[models.Realm]):

    class Meta:
        model = models.Realm
        fields = ("id", "name")


class ListCreateAccountSerializer(serializers.ModelSerializer[models.Account]):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    game_world = NestedPrimaryKeyRelatedField(GameWorldSerializer)
    realm = RealmSerializer(read_only=True, allow_null=True)
    players = UserSerializer(many=True, read_only=True, source="users")

    class Meta:
        model = models.Account
        fields = ("id", "name", "owner", "game_world", "realm", "race", "economy", "players")


class AccountDetailsSerializer(serializers.ModelSerializer[models.Account]):
    game_world = GameWorldSerializer(read_only=True)
    players = UserSerializer(many=True, read_only=True, source="users")

    class Meta:
        model = models.Account
        fields = ("id", "name", "owner", "game_world", "race", "economy", "players")
        read_only_fields = ("name", "race", "economy")

    def update(self, instance: models.Account, validated_data: Any) -> models.Account:
        instance.change_owner(validated_data["owner"])
        return instance


class JoinAccountSerializer(serializers.Serializer):
    id = serializers.UUIDField()

    def create(self, validated_data: Any) -> models.Account:
        user = self.context["request"].user
        account = get_object_or_404(models.Account, id=validated_data["id"])
        account.join_account(user)
        return account

    def to_representation(self, instance: models.Account) -> dict[str, Any]:
        """We want to return the actual account when we successfully join and return this serializer's data."""
        return AccountDetailsSerializer(instance).data


class JoinAccountSerializerExtension(OpenApiSerializerExtension):
    """OpenAPI Extension for DRF Spectacular so that it knows how the JoinAccountSerializer above behaves."""

    target_class = JoinAccountSerializer

    def map_serializer(
        self, auto_schema: AutoSchema, direction: Literal["request", "response"]
    ) -> dict[str, Any]:  # pragma: no cover
        if direction == "response":
            # In the response, we return the serialized account; let DRF Spectacular know that
            component = auto_schema.resolve_serializer(AccountDetailsSerializer, direction)
            return component.ref
        # Return the default value for the request (regular serialization)
        default: dict[str, Any] = auto_schema._map_serializer(self.target, direction, bypass_extensions=True)
        return default
