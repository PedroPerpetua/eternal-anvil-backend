from typing import Any, Optional
from uuid import UUID
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema
from realm_manager import models, serializers
from users.models import User
from users.view_mixins import AuthenticatedUserMixin


# GameWorlds -----------------------------------------------------------------


@extend_schema(tags=["Realm Manager - Game Worlds"])
class ListGameWorldView(AuthenticatedUserMixin, generics.ListAPIView):
    """Endpoint to list Game Worlds."""

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
    """Endpoint to join existing Accounts."""

    serializer_class = serializers.JoinAccountSerializer


must_be_owner_response = OpenApiResponse(
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


class TargetAccountMixin(AuthenticatedUserMixin):
    """Mixin to target the requested Account object."""

    def get_queryset(self) -> QuerySet:
        return models.Account.objects.filter(players__user=self.request.user)

    def validate_owner(self) -> None:
        """Validate that the user making the request is the owner of the account."""
        account: models.Account = self.get_object()
        if account.owner != self.request.user:
            raise PermissionDenied({"user": "You must be the account owner to perform this operation."})


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema(methods=["get"], description="Endpoint to retrieve an Account.")
@extend_schema(
    methods=["put"], description="Endpoint to update an Account's owner. Only the owner can call this endpoint."
)
@extend_schema(methods=["delete"], description="Endpoint to delete Accounts. Only the owner can call this endpoint.")
@extend_schema(methods=["delete", "put"], responses={403: must_be_owner_response})
class AccountDetailsView(TargetAccountMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.AccountDetailsSerializer
    # We don't want patch here
    http_method_names = ["get", "put", "delete"]

    def destroy(self, *args: Any, **kwargs: Any) -> Response:
        self.validate_owner()
        return super().destroy(*args, **kwargs)

    def update(self, *args: Any, **kwargs: Any) -> Response:
        self.validate_owner()
        return super().update(*args, **kwargs)


@extend_schema(tags=["Realm Manager - Accounts"])
class LeaveAccountView(TargetAccountMixin, generics.DestroyAPIView):
    """Endpoint to leave the Account."""

    def destroy(self, *args: Any, **kwargs: Any) -> Response:
        account: models.Account = self.get_object()
        account.leave_account(self.request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema(responses={403: must_be_owner_response})
class RemoveUserFromAccount(TargetAccountMixin, generics.DestroyAPIView):
    """Endpoint to remove a User from the Account. Only the owner can use this endpoint."""

    def destroy(self, *args: Any, user_id: Optional[UUID], **kwargs: Any) -> Response:
        self.validate_owner()
        account: models.Account = self.get_object()
        user = get_object_or_404(User, id=user_id)
        account.leave_account(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
