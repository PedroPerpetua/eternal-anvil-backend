from typing import Any
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from realm_manager import models


# GameWorlds -----------------------------------------------------------------


class ListGameWorld(serializers.ModelSerializer[models.GameWorld]):
    class Meta:
        model = models.GameWorld
        fields = ("id", "name", "code", "start", "end")


# Accounts -------------------------------------------------------------------


class ListCreateAccountSerializer(serializers.ModelSerializer[models.Account]):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.Account
        fields = ("id", "name", "owner", "game_world", "race", "economy")

    def create(self, validated_data: Any) -> models.Account:
        try:
            return super().create(validated_data)
        except DjangoValidationError as dve:
            raise serializers.ValidationError(serializers.as_serializer_error(dve)) from dve


class JoinAccountSerializer(serializers.Serializer):
    id = serializers.UUIDField()

    def create(self, validated_data: Any) -> models.Account:
        user = self.context["request"].user
        account = get_object_or_404(models.Account, id=validated_data["id"])
        try:
            account.join_account(user)
        except DjangoValidationError as dve:
            raise serializers.ValidationError(serializers.as_serializer_error(dve)) from dve
        return account


class AccountDetailsSerializer(serializers.ModelSerializer[models.Account]):
    class Meta:
        model = models.Account
        fields = ("id", "name", "owner", "game_world", "race", "economy")
        read_only_fields = ("id", "name", "game_world", "race", "economy")

    def update(self, instance: models.Account, validated_data: Any) -> models.Account:
        try:
            instance.change_owner(validated_data["owner"])
            return instance
        except DjangoValidationError as dve:
            raise serializers.ValidationError(serializers.as_serializer_error(dve)) from dve
