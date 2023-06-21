from django.conf import settings
from django.http import HttpResponse
from django_prometheus.exports import ExportToDjangoView
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def health_view(request):
    # TODO: Implement checks
    # https://tools.ietf.org/id/draft-inadarei-api-health-check-05.html
    return Response({'status': 'pass'})


def prometheus_exporter_view(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    auth_header_token = None
    if auth_header and auth_header.startswith('Bearer '):
        auth_header_token = auth_header[7:]
    get_parameter_token = request.GET.get('token')
    token = auth_header_token or get_parameter_token
    if token != settings.PROMETHEUS_METRICS_AUTH_TOKEN:
        return HttpResponse('Unauthorized', status=401)
    return ExportToDjangoView(request)
