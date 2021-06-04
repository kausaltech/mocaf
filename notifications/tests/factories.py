import datetime
from factory import LazyAttribute, SubFactory
from factory.django import DjangoModelFactory

from trips.tests.factories import DeviceFactory
from notifications.models import EventTypeChoices


class NotificationTemplateFactory(DjangoModelFactory):
    class Meta:
        model = 'notifications.NotificationTemplate'

    title_fi = "Title fi"
    title_en = "Title en"
    body_fi = "Body fi"
    body_en = "Body en"
    event_type = EventTypeChoices.WELCOME_MESSAGE


class NotificationLogEntryFactory(DjangoModelFactory):
    class Meta:
        model = 'notifications.NotificationLogEntry'

    device = SubFactory(DeviceFactory)
    template = SubFactory(NotificationTemplateFactory)
    sent_at = LazyAttribute(lambda f: f.device.created_at + datetime.timedelta(days=1))
