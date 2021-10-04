import csv
from django.http import HttpResponse, Http404
from .models import AreaType, DailyTripSummary


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

    if type != 'daily-trips':
        raise Http404()

    cols = ('date', 'origin_id', 'dest_id', 'mode_id', 'trips')

    vals = DailyTripSummary.objects.filter(origin__type=area_type, dest__type=area_type)\
        .values_list(*cols)

    resp = HttpResponse(content_type='text/csv')
    writer = csv.writer(resp)
    writer.writerow(cols)
    writer.writerows(vals)
    return resp
