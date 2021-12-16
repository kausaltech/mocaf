from django.utils.timezone import make_aware, utc
from factory import post_generation, Sequence, SubFactory
from factory.django import DjangoModelFactory
from datetime import datetime
from uuid import UUID


class DeviceFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.Device'

    uuid = Sequence(lambda i: UUID(int=i))
    account_key = Sequence(lambda i: UUID(int=i))  # will be set to None unless register_after_creation is set to True
    token = None
    platform = None
    system_version = None
    brand = None
    model = None
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
        if extracted is None:
            extracted = False
        # obj.account_key was set to something by Sequence. Set it to None if register_after_creation is not requested.
        account_key = obj.account_key
        assert account_key
        obj.account_key = None
        obj.save()
        if extracted is True:
            obj.register(account_key, migrate_existing=False)


class TransportModeFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.TransportMode'
        django_get_or_create = ('identifier',)

    identifier = 'bicycle'
    name = "Bicycle"
    emission_factor = 5.0


class TransportModeVariantFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.TransportModeVariant'
        django_get_or_create = ('mode', 'identifier',)

    mode = SubFactory(TransportModeFactory)
    identifier = 'good_old_bike'
    name = "Good old bike"
    emission_factor = 4.0


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


class BackgroundInfoQuestionFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.BackgroundInfoQuestion'

    device = SubFactory(DeviceFactory)
    question = 'Q'
    answer = 'A'


class DeviceDefaultModeVariantFactory(DjangoModelFactory):
    class Meta:
        model = 'trips.DeviceDefaultModeVariant'

    device = SubFactory(DeviceFactory)
    mode = SubFactory(TransportModeFactory)
    variant = SubFactory(TransportModeVariantFactory)
