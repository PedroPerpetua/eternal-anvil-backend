from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from extensions.utilities.types import URLPatternsList


urlpatterns: URLPatternsList = [
    path("", include("core.urls")),
    path("users/", include("users.urls")),
    path("realm-manager/", include("realm_manager.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
