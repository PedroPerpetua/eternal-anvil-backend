from typing import Any, Optional
from uuid import UUID
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
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

# Common OpenAPI errors
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

multi_account_response = OpenApiResponse(
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


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema_view(
    get=extend_schema(summary="Get account list", description="Endpoint to list Accounts."),
    post=extend_schema(
        summary="Create account",
        description="Endpoint to create Accounts.",
        responses={
            201: serializers.ListCreateAccountSerializer,
            403: multi_account_response,
        },
    ),
)
class ListCreateAccountView(AuthenticatedUserMixin, generics.ListCreateAPIView[models.Account]):
    serializer_class = serializers.ListCreateAccountSerializer

    def get_queryset(self) -> QuerySet[models.Account]:
        return models.Account.objects.filter(players__user=self.request.user)


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
@extend_schema_view(
    get=extend_schema(summary="Get account details", description="Endpoint to retrieve an Account."),
    put=extend_schema(
        summary="Update account details",
        description="Endpoint to update an Account's owner. Only the owner can call this endpoint.",
        responses={200: serializers.AccountDetailsSerializer, 403: must_be_owner_response},
    ),
    delete=extend_schema(
        summary="Delete account",
        description="Endpoint to delete Accounts. Only the owner can call this endpoint.",
        responses={204: OpenApiResponse(description="Account deleted successfully"), 403: must_be_owner_response},
    ),
)
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
@extend_schema_view(
    post=extend_schema(
        operation_id="realm_manager_accounts_join",
        summary="Join account",
        responses={
            200: serializers.JoinAccountSerializer,
            403: multi_account_response,
        },
    )
)
class JoinAccountView(AuthenticatedUserMixin, generics.CreateAPIView):
    """Endpoint to join existing Accounts."""

    serializer_class = serializers.JoinAccountSerializer


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema_view(
    delete=extend_schema(
        operation_id="realm_manager_accounts_leave",
        summary="Leave account",
        responses={
            204: OpenApiResponse(description="Left account successfully"),
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
                                    "code": {"enum": ["failed_remove_owner"]},
                                    "detail": {"enum": ["The owner of the account cannot be removed."]},
                                    "attr": {"enum": ["owner"]},
                                },
                                "required": ["code", "detail", "attr"],
                            },
                        },
                    },
                    "required": ["type", "errors"],
                },
                description="Is Owner",
            ),
        },
    )
)
class LeaveAccountView(TargetAccountMixin, generics.DestroyAPIView):
    """Endpoint to leave the Account."""

    # https://github.com/tfranzel/drf-spectacular/issues/308
    queryset = models.Account.objects.none()

    def destroy(self, *args: Any, **kwargs: Any) -> Response:
        account: models.Account = self.get_object()
        account.leave_account(self.request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Realm Manager - Accounts"])
@extend_schema_view(
    delete=extend_schema(
        operation_id="realm_manager_accounts_remove_user",
        summary="Remove user from account",
        responses={
            204: OpenApiResponse(description="User removed from the account successfully"),
            403: must_be_owner_response,
        },
    )
)
class RemoveUserFromAccount(TargetAccountMixin, generics.DestroyAPIView):
    """Endpoint to remove a User from the Account. Only the owner can use this endpoint."""

    # https://github.com/tfranzel/drf-spectacular/issues/308
    queryset = models.Account.objects.none()

    def destroy(self, *args: Any, user_id: Optional[UUID], **kwargs: Any) -> Response:
        self.validate_owner()
        account: models.Account = self.get_object()
        user = get_object_or_404(User, id=user_id)
        account.leave_account(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
