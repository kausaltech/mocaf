from django.utils import timezone
from rest_framework.decorators import api_view, schema
from rest_framework.response import Response

from .models import ReceiveData


@api_view(['POST'])
@schema(None)
def ingest_view(request):
    received_at = timezone.now()
    data = request.data
    obj = ReceiveData(data=data, received_at=received_at)
    obj.save()
    return Response({'ok': True, 'received_at': received_at})
