import pytest

pytestmark = pytest.mark.django_db


def test_carbon_footprint_summary(graphql_client_query_data, account, device1, leg1, leg2):
    assert leg1.trip.device != leg2.trip.device
    response = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!, $account: String, $startDate: Date!)
        @device(uuid: $uuid, token: $token, account: $account)
        {
          carbonFootprintSummary(startDate: $startDate, units: G) {
            carbonFootprint
          }
        }
        ''',
        variables={
            'uuid': str(device1.uuid),
            'token': str(device1.token),
            'account': account.key,
            'startDate': min(leg1.start_time, leg2.start_time).date().isoformat(),
        }
    )
    total_footprint = leg1.carbon_footprint + leg2.carbon_footprint
    assert response == {
        'carbonFootprintSummary': {
            'carbonFootprint': total_footprint,
        }
    }
