from django.conf import settings
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
# from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from trips_ingest.api import ingest_view, upload_log_view
from .graphql_views import MocafGraphQLView
from .views import health_view


urlpatterns = [
    path('django-admin/', admin.site.urls),

    path('admin/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('v1/health/', csrf_exempt(health_view)),
    path('v1/graphql/', csrf_exempt(MocafGraphQLView.as_view(graphiql=True))),
    path('v1/ingest/', csrf_exempt(ingest_view)),
    path('v1/upload-log/<slug:uuid>/', csrf_exempt(upload_log_view), name='upload-debug-log'),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# urlpatterns = urlpatterns + [
#     path("pages/", include(wagtail_urls)),
# ]
