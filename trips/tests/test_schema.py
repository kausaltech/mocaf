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


def test_leg_node(graphql_client_query_data, uuid, token, trip):
    leg = LegFactory(trip=trip)
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            legs {
              id
              mode {
                __typename
                id
              }
              modeConfidence
              startTime
              endTime
              startLoc
              endLoc
              length
              carbonFootprint
              nrPassengers
              deletedAt
              canUpdate
            }
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'trips': [{
            'legs': [{
                'id': str(leg.id),
                'mode': {
                    '__typename': 'TransportMode',
                    'id': str(leg.mode.id),
                },
                'modeConfidence': leg.mode_confidence,
                'startTime': leg.start_time.isoformat(),
                'endTime': leg.end_time.isoformat(),
                'startLoc': {
                    'type': 'Point',
                    'coordinates': [c for c in leg.start_loc],
                },
                'endLoc': {
                    'type': 'Point',
                    'coordinates': [c for c in leg.end_loc],
                },
                'length': leg.length,
                'carbonFootprint': leg.carbon_footprint,
                'nrPassengers': leg.nr_passengers,
                'deletedAt': leg.deleted_at,
                'canUpdate': leg.can_user_update(),
            }],
        }]
    }
    assert data == expected


def test_trip_missing_token(graphql_client_query, contains_error, uuid, trip):
    response = graphql_client_query(
        '''
        query($uuid: String!)
        @device(uuid: $uuid)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Token required')


def test_trip_missing_uuid(graphql_client_query, contains_error, uuid, token, trip):
    response = graphql_client_query(
        '''
        query($token: String!)
        @device(token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'token': token}
    )
    assert contains_error(response,
                          message='Directive "device" argument "uuid" of type "String!" is required but not provided.')


def test_trip_mocaf_not_enabled(graphql_client_query, contains_error, uuid, trip):
    assert trip.device.token is None
    token = '12345678-1234-1234-1234-123456789012'
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Invalid token')


def test_trip_invalid_token(graphql_client_query, contains_error, uuid, token, trip):
    invalid_token = '12345678-1234-1234-1234-123456789012'
    assert token != invalid_token
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': invalid_token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Invalid token')


def test_trip_mocaf_disabled(graphql_client_query, disable_mocaf, contains_error, uuid, token, trip):
    assert trip.device
    disable_mocaf(uuid, token)
    assert not trip.device.enabled
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Mocaf disabled')


def test_enable_mocaf_without_token(graphql_client_query_data, enable_mocaf, device, uuid):
    assert not device.enabled
    assert device.token is None
    token = enable_mocaf(uuid)
    assert token
    device.refresh_from_db()
    assert device.enabled
    assert device.token == token


def test_enable_mocaf_with_token(disable_mocaf, enable_mocaf, device):
    # To have a token, we need to have enabled Mocaf at least once. To enable Mocaf again, it must be disabled before.
    token = enable_mocaf(device.uuid)
    disable_mocaf(device.uuid, token)
    device.refresh_from_db()
    assert not device.enabled
    assert device.token == token
    enable_result = enable_mocaf(device.uuid, token)
    assert enable_result is None
    device.refresh_from_db()
    assert device.enabled
    assert device.token == token


def test_enable_mocaf_device_directive_missing(graphql_client_query, contains_error, uuid, token):
    # We want enableMocaf to complayn when the device already has a token but it's not supplied via the @device
    # directive.
    response = graphql_client_query(
        '''
        mutation($uuid: String!) {
          enableMocaf(uuid: $uuid) {
            ok
            token
          }
        }
        ''',
        variables={'uuid': uuid}
    )
    assert contains_error(response, message='Device exists, specify token with the @device directive')
