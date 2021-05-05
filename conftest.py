import json
import pytest
from graphene_django.utils.testing import graphql_query
from pytest_factoryboy import register

from trips.tests import factories as trips_factories

register(trips_factories.DeviceFactory)
register(trips_factories.TripFactory)


@pytest.fixture
def graphql_client_query(client):
    def func(*args, **kwargs):
        return graphql_query(*args, **kwargs, client=client, graphql_url='/v1/graphql/')
    return func


@pytest.fixture
def graphql_client_query_data(graphql_client_query):
    """Make a GraphQL request, make sure the `error` field is not present and return the `data` field."""
    def func(*args, **kwargs):
        response = graphql_client_query(*args, **kwargs)
        content = json.loads(response.content)
        assert 'errors' not in content
        return content['data']
    return func


@pytest.fixture
def uuid(device):
    return str(device.uuid)


@pytest.fixture
def token(graphql_client_query_data, uuid):
    data = graphql_client_query_data(
        '''
        mutation($uuid: UUID!) {
          enableMocaf(uuid: $uuid) {
            ok
            token
          }
        }
        ''',
        variables={'uuid': uuid}
    )
    data = data['enableMocaf']
    assert data['ok']
    token = data['token']
    return token
