import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils.timezone import make_aware, utc

from trips.tests.factories import AccountFactory, DeviceFactory, LegFactory, TripFactory
from trips.models import Account, Device, Leg, Trip

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


def test_only_list_own_trips(graphql_client_query_data, uuid, token, trip):
    LegFactory(trip=trip)
    other_device = DeviceFactory()
    assert other_device.uuid != uuid
    other_trip = TripFactory(device=other_device)
    LegFactory(trip=other_trip)
    data = graphql_client_query_data(
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
    expected = {
        'trips': [{
            'id': str(trip.id),
        }]
    }
    assert data == expected


def test_device_directive_missing_token(graphql_client_query, contains_error, uuid, trip):
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


def test_device_directive_missing_uuid(graphql_client_query, contains_error, uuid, token, trip):
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


def test_device_directive_mocaf_not_enabled(graphql_client_query, contains_error):
    device = DeviceFactory(enable_after_creation=False)
    assert device.token is None
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
        variables={'uuid': str(device.uuid), 'token': token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Invalid token')


def test_device_directive_invalid_token(graphql_client_query, contains_error, uuid, token, trip):
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


def test_device_directive_mocaf_disabled(graphql_client_query, disable_mocaf, contains_error, uuid, token, trip):
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


def test_enable_mocaf_without_token(graphql_client_query_data, enable_mocaf):
    device = DeviceFactory(enable_after_creation=False)
    assert not device.enabled
    assert device.token is None
    token = enable_mocaf(device.uuid)
    assert token
    device.refresh_from_db()
    assert device.enabled
    assert device.token == token


def test_enable_mocaf_with_token(disable_mocaf, enable_mocaf):
    device = DeviceFactory(enable_after_creation=False)
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
    # We want enableMocaf to complain when the device already has a token but it's not supplied via the @device
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


def test_device_directive_account_not_found(graphql_client_query, contains_error, uuid, token, trip):
    account_key = 'foo'
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!, $account: String)
        @device(uuid: $uuid, token: $token, account: $account)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token, 'account': account_key}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Account not found')


def test_device_directive_invalid_account(graphql_client_query, contains_error, uuid, token, trip, account):
    new_account = AccountFactory()
    assert new_account.key != account.key
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!, $account: String)
        @device(uuid: $uuid, token: $token, account: $account)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token, 'account': new_account.key}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Invalid account')


def test_trips_all_enabled_devices_of_account(graphql_client_query_data):
    account = AccountFactory()

    # We will only use the first device's token
    device1 = DeviceFactory(account=account, enable_after_creation=True)
    trip1 = TripFactory(device=device1)
    LegFactory(trip=trip1)

    # Enable mocaf also for second device, but won't use its token
    device2 = DeviceFactory(account=account, enable_after_creation=True)
    trip2 = TripFactory(device=device2)
    LegFactory(trip=trip2)

    # Don't enable mocaf for third device. Its trip should not show up.
    device3 = DeviceFactory(account=account, enable_after_creation=False)
    trip3 = TripFactory(device=device3)
    LegFactory(trip=trip3)

    assert account.devices.count() == 3
    response = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!, $account: String)
        @device(uuid: $uuid, token: $token, account: $account)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': str(device1.uuid), 'token': str(device1.token), 'account': account.key}
    )
    assert response == {
        'trips': [
            {'id': str(trip1.id)},
            {'id': str(trip2.id)},
        ]
    }


@pytest.mark.parametrize('reverse', [False, True])
def test_trips_ordered_by_time(graphql_client_query_data, reverse):
    if reverse:
        start1, start2 = make_aware(datetime(2020, 3, 2), utc), make_aware(datetime(2020, 3, 1), utc)
    else:
        start1, start2 = make_aware(datetime(2020, 3, 1), utc), make_aware(datetime(2020, 3, 2), utc)
    end1 = start1 + relativedelta(hours=1)
    end2 = start2 + relativedelta(hours=1)

    device = DeviceFactory()
    trip1 = TripFactory(device=device)
    LegFactory(trip=trip1, start_time=start1, end_time=end1)
    trip2 = TripFactory(device=device)
    LegFactory(trip=trip2, start_time=start2, end_time=end2)

    response = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips(orderBy: "startTime") {
            id
          }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    if reverse:
        expected_order = [trip2, trip1]
    else:
        expected_order = [trip1, trip2]
    assert response == {
        'trips': [{'id': str(trip.id)} for trip in expected_order]
    }


@pytest.mark.parametrize('reverse', [False, True])
def test_trips_ordered_by_time_different_devices(graphql_client_query_data, reverse):
    account = AccountFactory()

    if reverse:
        start1, start2 = make_aware(datetime(2020, 3, 2), utc), make_aware(datetime(2020, 3, 1), utc)
    else:
        start1, start2 = make_aware(datetime(2020, 3, 1), utc), make_aware(datetime(2020, 3, 2), utc)
    end1 = start1 + relativedelta(hours=1)
    end2 = start2 + relativedelta(hours=1)

    device1 = DeviceFactory(account=account)
    trip1 = TripFactory(device=device1)
    LegFactory(trip=trip1, start_time=start1, end_time=end1)

    device2 = DeviceFactory(account=account)
    trip2 = TripFactory(device=device2)
    LegFactory(trip=trip2, start_time=start2, end_time=end2)

    response = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!, $account: String)
        @device(uuid: $uuid, token: $token, account: $account)
        {
          trips(orderBy: "startTime") {
            id
          }
        }
        ''',
        variables={'uuid': str(device1.uuid), 'token': str(device1.token), 'account': account.key}
    )
    if reverse:
        expected_order = [trip2, trip1]
    else:
        expected_order = [trip1, trip2]
    assert response == {
        'trips': [{'id': str(trip.id)} for trip in expected_order]
    }


def test_trip_different_device(graphql_client_query_data, account, device1, leg1, leg2, trip2):
    response = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!, $account: String, $trip: ID!)
        @device(uuid: $uuid, token: $token, account: $account)
        {
          trip(id: $trip) {
            id
          }
        }
        ''',
        variables={'uuid': str(device1.uuid), 'token': str(device1.token), 'account': account.key, 'trip': trip2.id}
    )
    assert response == {
        'trip': {
            'id': str(trip2.id),
        }
    }


def test_clear_user_data(graphql_client_query_data, account, device1, device2, trip1, trip2, leg1, leg2):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!, $account: String)
        @device(uuid: $uuid, token: $token, account: $account) {
          clearUserData {
            ok
          }
        }
        ''',
        variables={'uuid': str(device1.uuid), 'token': str(device1.token), 'account': account.key}
    )
    assert data['clearUserData']['ok'] is True
    assert not Device.objects.filter(id__in=[device1.id, device2.id]).exists()
    assert not Account.objects.filter(id=account.id).exists()
    assert not Leg.objects.filter(id__in=[leg1.id, leg2.id]).exists()
    assert not Trip.objects.filter(id__in=[trip1.id, trip2.id]).exists()
