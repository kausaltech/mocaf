from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mocaf.utils import public_fields
from trips_ingest.models import Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = public_fields(Location)


class LocationList(APIView):
    def post(self, request, format=None):
        return
        data = request.data.copy()
        if 'lon' in data and 'lat' in data:
            lon = float(data['lon'])
            lat = float(data['lat'])
            loc = 'POINT(%f %f)' % (lon, lat)
            data['loc'] = loc

        serializer = LocationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
