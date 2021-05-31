from datetime import datetime, timedelta
import logging
import orjson
from django.utils import timezone
from dateutil.parser import isoparse
import requests
from .rt_import import TransitRTImporter

logger = logging.getLogger(__name__)


GRAPHQL_QUERY = """
{
  currentlyRunningTrains(where: {
    trainType: {
      trainCategory: {
        or: [
          {name: {equals: "Long-distance"}},
          {name: {equals: "Commuter"}}
        ]
      }
    }
  }) {
    trainNumber
    departureDate
    commuterLineid
    trainType {
      name
      trainCategory {
        name
      }
    }
    operator {
      shortCode
    }
    trainLocations(orderBy: {timestamp: DESCENDING}, take: 1) {
      speed
      timestamp
      location
    }
  }
}
"""

URL = 'https://rata.digitraffic.fi/api/v1/train-locations/latest/'
GRAPHQL_URL = 'https://rata.digitraffic.fi/api/v2/graphql/graphql'


class RataImporter(TransitRTImporter):
    def perform_http_query(self):
        resp = requests.post(GRAPHQL_URL, json={'query': GRAPHQL_QUERY}, timeout=(10, 30))
        resp.raise_for_status()
        return resp.content

    def import_vehicle_activity(self, d):
        if 'trainLocations' not in d:
            return None

        if d['commuterLineid']:
            route_ref = d['commuterLineid']
        else:
            route_ref = '%s %s' % (d['trainType']['name'], d['trainNumber'])
        route = self.get_route(route_ref)
        if route is None:
            logger.warn('Route not found: %s' % route_ref)
            print(d)
        else:
            route = route.pk

        journey_ref = '%s:%s' % (d['departureDate'], route_ref)
        vehicle_ref = d['trainNumber']

        train_loc = d['trainLocations'][0]
        coords = train_loc['location']

        act = dict(
            vehicle_ref=vehicle_ref,
            direction_ref=None,
            journey_ref=route_ref,
            vehicle_journey_ref='%s:%s' % (journey_ref, vehicle_ref),
            speed=train_loc['speed'],
            time=isoparse(train_loc['timestamp']),
            loc=dict(lat=coords[1], lon=coords[0]),
            route_type=self.ROUTE_TYPE_TRAIN,
            route=route,
        )
        return act

    def update_from_data(self, data: bytes, data_ts: datetime = None):
        if data_ts is None:
            data_ts = timezone.now()
        data = orjson.loads(data)
        data = data['data']['currentlyRunningTrains']
        for train in data:
            act = self.import_vehicle_activity(train)
            if act is None:
                continue
            self.add_vehicle_activity(act, data_ts=data_ts)
