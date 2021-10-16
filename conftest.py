import json
import pytest
from graphene_django.utils.testing import graphql_query
from pytest_factoryboy import register

from trips.tests import factories as trips_factories

register(trips_factories.AccountFactory)
register(trips_factories.DeviceFactory)
register(trips_factories.TripFactory)


@pytest.fixture
def graphql_client_query(client):
    def func(*args, **kwargs):
        response = graphql_query(*args, **kwargs, client=client, graphql_url='/v1/graphql/')
        return json.loads(response.content)
    return func


@pytest.fixture
def graphql_client_query_data(graphql_client_query):
    """Make a GraphQL request, make sure the `error` field is not present and return the `data` field."""
    def func(*args, **kwargs):
        response = graphql_client_query(*args, **kwargs)
        assert 'errors' not in response
        return response['data']
    return func


@pytest.fixture
def uuid(device):
    return str(device.uuid)


@pytest.fixture
def contains_error():
    def func(response, code=None, message=None):
        if 'errors' not in response:
            return False
        expected_parts = {}
        if code is not None:
            expected_parts['extensions'] = {'code': code}
        if message is not None:
            expected_parts['message'] = message
        return any(expected_parts.items() <= error.items() for error in response['errors'])
    return func


@pytest.fixture
def disable_mocaf(graphql_client_query_data):
    def func(uuid, token):
        data = graphql_client_query_data(
            '''
            mutation($uuid: String!, $token: String!) @device(uuid: $uuid, token: $token) {
              disableMocaf {
                ok
              }
            }
            ''',
            variables={'uuid': str(uuid), 'token': token}
        )
        expected = {
            'disableMocaf': {
                'ok': True,
            }
        }
        assert data == expected
    return func


@pytest.fixture
def enable_mocaf(graphql_client_query_data):
    def func(uuid, token=None):
        if token is None:
            data = graphql_client_query_data(
                '''
                mutation($uuid: String!) {
                  enableMocaf(uuid: $uuid) {
                    ok
                    token
                  }
                }
                ''',
                variables={'uuid': str(uuid)}
            )
        else:
            data = graphql_client_query_data(
                '''
                mutation($uuid: String!, $token: String!) @device(uuid: $uuid, token: $token) {
                  enableMocaf {
                    ok
                    token
                  }
                }
                ''',
                variables={'uuid': str(uuid), 'token': token}
            )
        data = data['enableMocaf']
        assert data['ok']
        # assert data['token']  # if we ran enableMocaf with the @device directive, this will be None
        return data['token']
    return func


@pytest.fixture
def token(device):
    assert device.enabled
    assert device.token
    return str(device.token)


@pytest.fixture
def device1(account):
    """A device linked to `account`"""
    return trips_factories.DeviceFactory(account=account)


@pytest.fixture
def device2(account):
    """Another device linked to `account`"""
    return trips_factories.DeviceFactory(account=account)


@pytest.fixture
def trip1(device1):
    return trips_factories.TripFactory(device=device1)


@pytest.fixture
def trip2(device2):
    return trips_factories.TripFactory(device=device2)


@pytest.fixture
def leg1(trip1):
    return trips_factories.LegFactory(trip=trip1)


@pytest.fixture
def leg2(trip2):
    return trips_factories.LegFactory(trip=trip2)


@pytest.fixture
def register_device(graphql_client_query_data):
    def func(uuid, token, account_key):
        data = graphql_client_query_data(
            '''
            mutation($uuid: String!, $token: String!, $accountKey: String!)
            @device(uuid: $uuid, token: $token)
            {
              registerDevice(accountKey: $accountKey) {
                ok
              }
            }
            ''',
            variables={'uuid': str(uuid), 'token': token, 'accountKey': account_key}
        )
        assert data['registerDevice']['ok']
    return func
