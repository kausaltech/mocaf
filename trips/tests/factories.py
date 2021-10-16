from django.utils.timezone import make_aware, utc
from factory import post_generation, Sequence, SubFactory
from factory.django import DjangoModelFactory
from datetime import datetime
from uuid import UUID


class AccountFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.Account'

    key = None


class DeviceFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.Device'

    uuid = Sequence(lambda i: UUID(int=i))
    token = None
    platform = None
    system_version = None
    brand = None
    model = None
    account = SubFactory(AccountFactory)
    enabled_at = None
    created_at = make_aware(datetime(2020, 1, 1, 0, 0), utc)

    @post_generation
    def enable_after_creation(obj, create, extracted, **kwargs):
        if not create:
            return
        # Enable by default
        if extracted is None:
            extracted = True
        if extracted is True:
            time = make_aware(datetime(2020, 1, 1, 0, 0), utc)
            obj.set_enabled(True, time)
            obj.refresh_from_db()
            obj.generate_token()
            obj.save()

    @post_generation
    def register_after_creation(obj, create, extracted, **kwargs):
        if not create:
            return
        # Do not register by default
        if extracted is None:
            extracted = False
        if extracted is True:
            assert obj.account.key is None
            obj.account.generate_key()
            obj.account.save()
            obj.account.regenerate_all_carbon_footprints()


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
