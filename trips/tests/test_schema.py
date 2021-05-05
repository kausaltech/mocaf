import pytest

from trips.tests.factories import LegFactory

pytestmark = pytest.mark.django_db


def test_trip_node(graphql_client_query_data, uuid, token, trip):
    leg = LegFactory(trip=trip)
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
            deletedAt
            legs {
              __typename
              id
            }
            startTime
            endTime
            carbonFootprint
            length
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'trips': [{
            'id': str(trip.id),
            'deletedAt': None if trip.deleted_at is None else trip.deleted_at.isoformat(),
            'legs': [{
                '__typename': 'Leg',
                'id': str(leg.id),
            }],
            'startTime': leg.start_time.isoformat(),
            'endTime': leg.end_time.isoformat(),
            'carbonFootprint': trip.carbon_footprint,
            'length': trip.length,
        }]
    }
    assert data == expected

# TODO
# Requests should fail without enableMocaf or after disableMocaf
# enableMocaf multiple times should fail and keep token
