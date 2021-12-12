import csv
from django.http.response import HttpResponseBadRequest
import orjson

import requests
from django.conf import settings
from django.http import Http404, HttpResponse

from .models import AreaType, DailyModeSummary, DailyTripSummary


def area_type_topojson(request, id: int):
    try:
        area_type = AreaType.objects.values('topojson').get(id=id)
    except AreaType.DoesNotExist:
        raise Http404()

    return HttpResponse(area_type['topojson'], content_type='application/json')


def area_type_stats(request, id: int, type: str):
    try:
        area_type = AreaType.objects.get(id=id)
    except AreaType.DoesNotExist:
        raise Http404()

    if type == 'daily-trips':
        col_names = ('date', 'origin_area', 'dest_area', 'mode', 'trips')
        cols = ('date', 'origin__identifier', 'dest__identifier', 'mode__identifier', 'trips')
        vals = DailyTripSummary.objects.filter(origin__type=area_type, dest__type=area_type)\
            .values_list(*cols)
    elif type == 'daily-lengths':
        col_names = ('date', 'area', 'mode', 'length')
        cols = ('date', 'area__identifier', 'mode__identifier', 'length')
        vals = DailyModeSummary.objects.filter(area__type=area_type)\
            .values_list(*cols)
    else:
        raise Http404()

    resp = HttpResponse(content_type='text/csv')
    writer = csv.writer(resp)
    writer.writerow(col_names)
    writer.writerows(vals)
    return resp


def cubejs_api_request(request):
    """
    try:
        data = orjson.loads(request.body)
    except Exception as e:
        print(e)
        return HttpResponseBadRequest()
    """
    resp = requests.get(
        settings.CUBEJS_URL + request.path,
        params=request.GET
    )
    return HttpResponse(
        content=resp.content,
        content_type=resp.headers['content-type'],
        status=resp.status_code,
    )
