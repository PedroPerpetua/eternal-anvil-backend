from django.urls import include, path
from extensions.utilities.types import URLPatternsList
from realm_manager import views


app_name = "realm_manager"


urlpatterns: URLPatternsList = [
    path("game-worlds/", views.ListGameWorldView.as_view(), name="game-world-list"),
    path(
        "accounts/",
        include(
            (
                [
                    path("", views.ListCreateAccountView.as_view(), name="list-create"),
                    path("join/", views.JoinAccountView.as_view(), name="join"),
                    path("<uuid:pk>/", views.AccountDetailsView.as_view(), name="details"),
                ],
                "accounts",
            )
        ),
    ),
]
