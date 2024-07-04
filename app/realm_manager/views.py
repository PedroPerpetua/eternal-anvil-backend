from typing import Any, cast
from django.db.models.query import QuerySet
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema
from realm_manager import models, serializers
from users.view_mixins import AuthenticatedUserMixin


# GameWorlds -----------------------------------------------------------------


@extend_schema(tags=["Realm Manager - Game Worlds"])
@extend_schema(description="Endpoint to list Game Worlds.")
class ListGameWorldView(AuthenticatedUserMixin, generics.ListAPIView):
    serializer_class = serializers.ListGameWorld
    queryset = models.GameWorld.objects.all()


# Accounts -------------------------------------------------------------------


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema(methods=["get"], description="Endpoint to list Accounts.")
@extend_schema(methods=["post"], description="Endpoint to create Accounts.")
class ListCreateAccountView(AuthenticatedUserMixin, generics.ListCreateAPIView[models.Account]):
    serializer_class = serializers.ListCreateAccountSerializer

    def get_queryset(self) -> QuerySet[models.Account]:
        return models.Account.objects.filter(players__user=self.request.user)


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema(description="Endpoint to join existing Accounts.")
@extend_schema(
    responses={
        # Registration disabled
        403: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "type": {"enum": ["validation_error"]},
                    "errors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"enum": ["multi_account"]},
                                "detail": {"enum": ["User is already present in this game world."]},
                                "attr": {"enum": ["user"]},
                            },
                            "required": ["code", "detail", "attr"],
                        },
                    },
                },
                "required": ["type", "errors"],
            },
            description="Multi Account",
        )
    }
)
class JoinAccountView(AuthenticatedUserMixin, generics.CreateAPIView):
    serializer_class = serializers.JoinAccountSerializer


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema(methods=["get"], description="Endpoint to retrieve an Account.")
@extend_schema(
    methods=["put"], description="Endpoint to update an Account's owner. Only the owner can call this endpoint."
)
@extend_schema(methods=["delete"], description="Endpoint to delete Accounts. Only the owner can call this endpoint.")
@extend_schema(
    methods=["put", "delete"],
    responses={
        # Registration disabled
        403: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "type": {"enum": ["client_error"]},
                    "errors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"enum": [PermissionDenied.default_code]},
                                "detail": {"enum": ["You must be the account owner to perform this operation."]},
                                "attr": {"enum": ["user"]},
                            },
                            "required": ["code", "detail", "attr"],
                        },
                    },
                },
                "required": ["type", "errors"],
            },
            description="Not Owner",
        )
    },
)
class AccountDetailsView(AuthenticatedUserMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.AccountDetailsSerializer
    # We don't want patch here
    http_method_names = ["get", "put", "delete"]

    def get_queryset(self) -> QuerySet:
        return models.Account.objects.filter(players__user=self.request.user)

    def validate_owner(self) -> None:
        account = cast(models.Account, self.get_object())
        if account.owner != self.request.user:
            raise PermissionDenied({"user": "You must be the account owner to perform this operation."})

    def destroy(self, *args: Any, **kwargs: Any) -> Response:
        self.validate_owner()
        return super().destroy(*args, **kwargs)

    def update(self, *args: Any, **kwargs: Any) -> Response:
        self.validate_owner()
        return super().update(*args, **kwargs)
