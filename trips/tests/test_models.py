import pytest
from datetime import date, datetime
from django.utils.timezone import make_aware, utc

from budget.tests.factories import DeviceDailyCarbonFootprintFactory, PrizeFactory
from budget.enums import TimeResolution
from trips.tests.factories import (
    BackgroundInfoQuestionFactory, DeviceDefaultModeVariantFactory, DeviceFactory, LegFactory, TripFactory
)
from trips.generate import make_point
from trips.models import Device
from trips_ingest.models import DeviceHeartbeat, Location

pytestmark = pytest.mark.django_db


def test_update_daily_carbon_footprint_padding_on_idle_days(emission_budget_level_bronze):
    device = DeviceFactory()
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
    device.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                         make_aware(datetime(2020, 3, 1, 0, 0), utc))
    # For the days on which there are no trips and we don't know if the device moved, the bronze-level footprint is used
    if month.month == 1:
        expected = 5 + 30 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    elif month.month == 2:
        expected = 3 + 28 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    assert device.monthly_carbon_footprint(month) == pytest.approx(expected)


def test_monthly_carbon_footprint_device_stationary(emission_budget_level_bronze):
    month = date(2020, 1, 1)
    device = DeviceFactory()
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
    device.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                         make_aware(datetime(2020, 2, 1, 0, 0), utc))
    expected = 5 + 2 * 0 + 28 * emission_budget_level_bronze.calculate_for_date(month, TimeResolution.DAY)
    assert device.monthly_carbon_footprint(month) == pytest.approx(expected)


def test_num_active_days():
    device = DeviceFactory()
    num_active_days = 3
    for i in range(num_active_days):
        LegFactory(trip__device=device,
                   start_time=make_aware(datetime(2020, 1, i+1, 0, 0), utc),
                   end_time=make_aware(datetime(2020, 1, i+1, 0, 30), utc))
    device.update_daily_carbon_footprint(make_aware(datetime(2020, 1, 1, 0, 0), utc),
                                         make_aware(datetime(2020, 2, 1, 0, 0), utc))
    assert device.num_active_days(make_aware(datetime(2020, 1, 1, 0, 0))) == num_active_days


def test_device_register_sets_account_key():
    device = DeviceFactory()
    assert not device.account_key
    account_key = '12345678-1234-1234-1234-123456789012'
    assert not Device.objects.filter(account_key=account_key).exists()
    device.register(account_key)
    device.refresh_from_db()
    assert device.account_key == account_key


def test_device_register_removes_account_key_from_old_device(registered_device):
    assert registered_device.account_key
    new_device = DeviceFactory()
    new_device.register(registered_device.account_key)
    registered_device.refresh_from_db()
    assert not registered_device.account_key


def test_device_register_already_registered(registered_device):
    with pytest.raises(Exception):
        registered_device.register(registered_device.account_key)


def test_device_register_moves_trip(registered_device):
    trip = TripFactory(device=registered_device)
    assert list(registered_device.trips.all()) == [trip]
    new_device = DeviceFactory()
    new_device.register(registered_device.account_key)
    assert not registered_device.trips.exists()
    assert list(new_device.trips.all()) == [trip]


def test_device_register_moves_background_info_question(registered_device):
    question = BackgroundInfoQuestionFactory(device=registered_device)
    assert list(registered_device.background_info_questions.all()) == [question]
    new_device = DeviceFactory()
    new_device.register(registered_device.account_key)
    assert not registered_device.background_info_questions.exists()
    assert list(new_device.background_info_questions.all()) == [question]


def test_device_register_does_not_move_background_info_question_if_one_exists(registered_device):
    question = BackgroundInfoQuestionFactory(device=registered_device)
    new_device = DeviceFactory()
    new_question = BackgroundInfoQuestionFactory(device=new_device)
    new_device.register(registered_device.account_key)
    assert list(registered_device.background_info_questions.all()) == [question]
    assert list(new_device.background_info_questions.all()) == [new_question]


def test_device_register_moves_default_mode_variant(registered_device):
    variant = DeviceDefaultModeVariantFactory(device=registered_device)
    assert list(registered_device.default_mode_variants.all()) == [variant]
    new_device = DeviceFactory()
    new_device.register(registered_device.account_key)
    assert not registered_device.default_mode_variants.exists()
    assert list(new_device.default_mode_variants.all()) == [variant]


def test_device_register_does_not_move_default_mode_variant_if_one_exists(registered_device):
    variant = DeviceDefaultModeVariantFactory(device=registered_device)
    new_device = DeviceFactory()
    new_variant = DeviceDefaultModeVariantFactory(device=new_device)
    new_device.register(registered_device.account_key)
    assert list(registered_device.default_mode_variants.all()) == [variant]
    assert list(new_device.default_mode_variants.all()) == [new_variant]


def test_device_register_moves_daily_carbon_footprint(registered_device):
    footprint = DeviceDailyCarbonFootprintFactory(device=registered_device)
    assert list(registered_device.daily_carbon_footprints.all()) == [footprint]
    new_device = DeviceFactory()
    new_device.register(registered_device.account_key)
    assert not registered_device.daily_carbon_footprints.exists()
    assert list(new_device.daily_carbon_footprints.all()) == [footprint]


def test_device_register_moves_prize(registered_device):
    prize = PrizeFactory(device=registered_device)
    assert list(registered_device.prizes.all()) == [prize]
    new_device = DeviceFactory()
    new_device.register(registered_device.account_key)
    assert not registered_device.prizes.exists()
    assert list(new_device.prizes.all()) == [prize]
