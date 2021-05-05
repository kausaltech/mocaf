from django.utils.timezone import make_aware, utc
from factory import SubFactory
from factory.django import DjangoModelFactory
from datetime import datetime
from uuid import UUID


class DeviceFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.Device'

    uuid = UUID('f8d65ee8-4b3c-40d0-83fa-8351997120a3')
    token = None
    platform = None
    system_version = None
    brand = None
    model = None
    created_at = make_aware(datetime(2020, 1, 1, 0, 0), utc)


class TransportModeFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.TransportMode'
        django_get_or_create = ('identifier',)

    identifier = 'bicycle'
    name = "Bicycle"
    emission_factor = 5.0


class TripFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.Trip'

    device = SubFactory(DeviceFactory)
    deleted_at = None


class LegFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.Leg'

    trip = SubFactory(TripFactory)
    deleted_at = None
    mode = SubFactory(TransportModeFactory)
    mode_variant = None
    estimated_mode = None
    mode_confidence = None
    user_corrected_mode = None
    user_corrected_mode_variant = None
    start_time = make_aware(datetime(2020, 1, 1, 12, 0), utc)
    end_time = make_aware(datetime(2020, 1, 1, 12, 10), utc)
    start_loc = '0101000020E6100000731074B4AA0738405523168CA5C24E40'
    end_loc = '0101000020E610000048A5D8D13806384067FA25E2ADC24E40'
    length = 1860.702302423133
    carbon_footprint = 9303.511512115665
    nr_passengers = 0
