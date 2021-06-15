import pytest
from datetime import datetime
from django.utils.timezone import make_aware, utc

from budget.models import EmissionBudgetLevel
from trips.tests.factories import DeviceFactory, LegFactory, TripFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def bronze_level():
    return EmissionBudgetLevel.objects.create(identifier='bronze',
                                              carbon_footprint=123,
                                              year=2020)


def test_update_daily_carbon_footprint_padding_on_idle_days(bronze_level):
    device = DeviceFactory()
    trip1 = TripFactory(device=device)
    start_time = make_aware(datetime(2020, 1, 1, 0, 0), utc)
    end_time = make_aware(datetime(2020, 1, 3, 20, 0), utc)
    LegFactory(trip=trip1,
               start_time=start_time,
               end_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               carbon_footprint=1)
    LegFactory(trip=trip1,
               start_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               end_time=make_aware(datetime(2020, 1, 1, 1, 30), utc),
               carbon_footprint=2)
    trip2 = TripFactory(device=device)
    LegFactory(trip=trip2,
               start_time=make_aware(datetime(2020, 1, 3, 19, 0), utc),
               end_time=end_time,
               carbon_footprint=5)
    # There is no leg on 2020-01-02, so there the bronze level budget should be used

    assert not device.daily_carbon_footprints.exists()
    device.update_daily_carbon_footprint(start_time, end_time)
    assert device.daily_carbon_footprints.count() == 3
    expected = [3.0, bronze_level.carbon_footprint, 5.0]
    assert list(device.daily_carbon_footprints.values_list('carbon_footprint', flat=True)) == expected
