import pytest
from datetime import date, datetime
from django.utils.timezone import make_aware, utc

from budget.enums import TimeResolution
from trips.tests.factories import DeviceFactory, LegFactory, TripFactory
from trips.generate import make_point
from trips_ingest.models import DeviceHeartbeat, Location

pytestmark = pytest.mark.django_db


def test_update_daily_carbon_footprint_padding_on_idle_days(emission_budget_level_bronze):
    device = DeviceFactory()
    account = device.account
    trip1 = TripFactory(device=device)
    start_time = make_aware(datetime(2020, 1, 1, 0, 0), utc)
    end_time = make_aware(datetime(2020, 1, 3, 20, 0), utc)
    LegFactory(trip=trip1,
               start_time=start_time,
               end_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               carbon_footprint=1000)
    LegFactory(trip=trip1,
               start_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               end_time=make_aware(datetime(2020, 1, 1, 1, 30), utc),
               carbon_footprint=2000)
    trip2 = TripFactory(device=device)
    LegFactory(trip=trip2,
               start_time=make_aware(datetime(2020, 1, 3, 19, 0), utc),
               end_time=end_time,
               carbon_footprint=5000)
    # There is no leg on 2020-01-02, so there the bronze level budget should be used

    assert not account.daily_carbon_footprints.exists()
    account.update_daily_carbon_footprint(start_time, end_time)
    assert account.daily_carbon_footprints.count() == 3
    expected = [3.0, emission_budget_level_bronze.calculate_for_date(date(2020, 1, 2), TimeResolution.DAY), 5.0]
    assert list(account.daily_carbon_footprints.values_list('carbon_footprint', flat=True)) == expected


@pytest.mark.parametrize('month', [
    (date(2020, 1, 1)),
    (date(2020, 1, 31)),
    (date(2020, 2, 1)),
    (date(2020, 2, 15)),
])
def test_monthly_carbon_footprint(month, emission_budget_level_bronze):
    device = DeviceFactory()
    account = device.account
    # 1 leg in January, total footprint 5 kg
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 1, 1, 0, 0), utc),
               end_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               carbon_footprint=5000)
    # 2 legs in February, total footprint 3 kg
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 2, 1, 0, 0), utc),
               end_time=make_aware(datetime(2020, 2, 1, 0, 30), utc),
               carbon_footprint=1000)
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 2, 1, 0, 30), utc),
               end_time=make_aware(datetime(2020, 2, 1, 1, 30), utc),
               carbon_footprint=2000)
    account.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                          make_aware(datetime(2020, 3, 1, 0, 0), utc))
    # For the days on which there are no trips and we don't know if the device moved, the bronze-level footprint is used
    if month.month == 1:
        expected = 5 + 30 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    elif month.month == 2:
        expected = 3 + 28 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    assert account.monthly_carbon_footprint(month) == pytest.approx(expected)


def test_monthly_carbon_footprint_device_stationary(emission_budget_level_bronze):
    month = date(2020, 1, 1)
    device = DeviceFactory()
    account = device.account
    # 1 leg in January, total footprint 5 kg
    LegFactory(trip__device=device,
               start_time=make_aware(datetime(2020, 1, 1, 0, 0), utc),
               end_time=make_aware(datetime(2020, 1, 1, 0, 30), utc),
               carbon_footprint=5000)
    # For the days on which there are no trips and the device was stationary, assume 0 emissions.
    # A device is considered stationary on a day if it has a DeviceHeartbeat or Location on that day.
    DeviceHeartbeat.objects.create(time=make_aware(datetime(2020, 1, 2, 0, 0), utc),
                                   uuid=device.uuid)
    Location.objects.create(time=make_aware(datetime(2020, 1, 3, 0, 0), utc),
                            uuid=device.uuid,
                            loc=make_point(0, 0))
    account.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                          make_aware(datetime(2020, 2, 1, 0, 0), utc))
    expected = 5 + 2 * 0 + 28 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    assert account.monthly_carbon_footprint(month) == pytest.approx(expected)


def test_num_active_days():
    device = DeviceFactory()
    account = device.account
    num_active_days = 3
    for i in range(num_active_days):
        LegFactory(trip__device=device,
                   start_time=make_aware(datetime(2020, 1, i+1, 0, 0), utc),
                   end_time=make_aware(datetime(2020, 1, i+1, 0, 30), utc))
    account.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                          make_aware(datetime(2020, 2, 1, 0, 0), utc))
    assert account.num_active_days(make_aware(datetime(2020, 1, 1, 0, 0))) == num_active_days
