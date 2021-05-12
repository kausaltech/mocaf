from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def health_view(request):
    # TODO: Implement checks
    # https://tools.ietf.org/id/draft-inadarei-api-health-check-05.html
    return Response({'status': 'pass'})
