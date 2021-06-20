import pytest
from datetime import date, datetime
from django.utils.timezone import make_aware, utc

from budget.enums import TimeResolution
from trips.tests.factories import DeviceFactory, LegFactory, TripFactory

pytestmark = pytest.mark.django_db


def test_update_daily_carbon_footprint_padding_on_idle_days(emission_budget_level_bronze):
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
    expected = [3.0, emission_budget_level_bronze.calculate_for_date(date(2020, 1, 2), TimeResolution.DAY), 5.0]
    assert list(device.daily_carbon_footprints.values_list('carbon_footprint', flat=True)) == expected


@pytest.mark.parametrize('month', [
    (date(2020, 1, 1)),
    (date(2020, 1, 31)),
    (date(2020, 2, 1)),
    (date(2020, 2, 15)),
])
def test_monthly_carbon_footprint(month, emission_budget_level_bronze):
    device = DeviceFactory()
    # 1 leg in January, total footprint 5
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 1, 1, 0, 0), utc),
               end_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               carbon_footprint=5)
    # 2 legs in February, total footprint 3
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 2, 1, 0, 0), utc),
               end_time=make_aware(datetime(2020, 2, 1, 0, 30), utc),
               carbon_footprint=1)
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 2, 1, 0, 30), utc),
               end_time=make_aware(datetime(2020, 2, 1, 1, 30), utc),
               carbon_footprint=2)
    device.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                         make_aware(datetime(2020, 3, 1, 0, 0), utc))
    # For the days on which there are no trips, the bronze-level footprint is used
    if month.month == 1:
        expected = 5 + 30 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    elif month.month == 2:
        expected = 3 + 28 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    assert device.monthly_carbon_footprint(month) == expected
