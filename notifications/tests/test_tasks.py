import datetime
import json
import pytest
import responses
from dateutil.relativedelta import relativedelta
from django.utils.timezone import make_aware, utc

from trips.tests.factories import DeviceFactory
from notifications import tasks
from notifications.models import EventTypeChoices, NotificationLogEntry
from notifications.tests.factories import NotificationLogEntryFactory, NotificationTemplateFactory

pytestmark = pytest.mark.django_db

API_URL = 'https://example.com/'
SUCCESS_RESPONSE = {
    'ok': True,
    'message': 'success',
}


@pytest.fixture
def api_settings(settings):
    settings.GENIEM_NOTIFICATION_API_BASE = API_URL
    settings.GENIEM_NOTIFICATION_API_TOKEN = 'test'


def test_welcome_notification_devices():
    device = DeviceFactory()
    today = device.created_at.date() + datetime.timedelta(days=1)
    result = list(tasks.welcome_notification_devices(today))
    assert result == [device]


def test_welcome_notification_devices_already_sent():
    device = DeviceFactory()
    NotificationLogEntryFactory(device=device,
                                template__event_type=EventTypeChoices.WELCOME_MESSAGE)
    today = device.created_at.date() + datetime.timedelta(days=1)
    result = list(tasks.welcome_notification_devices(today))
    assert result == []


def test_welcome_notification_devices_too_old():
    device = DeviceFactory()
    today = device.created_at.date() + datetime.timedelta(days=2)
    result = list(tasks.welcome_notification_devices(today))
    assert result == []


@responses.activate
def test_send_welcome_notifications_records_sending(api_settings):
    device = DeviceFactory()
    template = NotificationTemplateFactory()
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(now)
    log_entries = list(NotificationLogEntry.objects.all())
    assert len(log_entries) == 1
    assert log_entries[0].device == device
    assert log_entries[0].template == template
    assert log_entries[0].sent_at == now


@responses.activate
def test_send_welcome_notifications_sends_notification(api_settings):
    device = DeviceFactory()
    template = NotificationTemplateFactory(event_type=EventTypeChoices.WELCOME_MESSAGE)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(now)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == API_URL
    expected_body = {
        'uuids': [str(device.uuid)],
        'titleEn': template.render('title', 'en'),
        'titleFi': template.render('title', 'fi'),
        'contentEn': template.render('body', 'en'),
        'contentFi': template.render('body', 'fi'),
    }
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == expected_body


def test_monthly_summary_notification_devices_no_prior_summary():
    device = DeviceFactory()
    today = device.created_at.date() + relativedelta(months=1)
    result = list(tasks.monthly_summary_notification_devices(today))
    assert result == [device]


@pytest.mark.parametrize('today', [
    datetime.date(2020, 3, 1),
    datetime.date(2020, 3, 15),
    datetime.date(2020, 3, 31),
])
@pytest.mark.parametrize('last_notification_sent_at', [
    datetime.datetime(2020, 2, 1),  # beginning of last month
    datetime.datetime(2020, 2, 15),  # middle of last month
    datetime.datetime(2020, 2, 29),  # end of last month
    datetime.datetime(2020, 1, 31),  # older than last month
])
def test_monthly_summary_notification_devices(today, last_notification_sent_at):
    device = DeviceFactory()
    NotificationLogEntryFactory(device=device,
                                template__event_type=EventTypeChoices.MONTHLY_SUMMARY,
                                sent_at=make_aware(last_notification_sent_at, utc))
    result = list(tasks.monthly_summary_notification_devices(today))
    assert result == [device]


@pytest.mark.parametrize('last_notification_sent_at', [
    datetime.datetime(2020, 3, 1),
    datetime.datetime(2020, 3, 15),
    datetime.datetime(2020, 3, 31),
])
def test_monthly_summary_notification_devices_already_sent(last_notification_sent_at):
    today = datetime.date(2020, 3, 31)
    device = DeviceFactory()
    NotificationLogEntryFactory(device=device,
                                template__event_type=EventTypeChoices.MONTHLY_SUMMARY,
                                sent_at=make_aware(last_notification_sent_at, utc))
    result = list(tasks.monthly_summary_notification_devices(today))
    assert result == []


@responses.activate
def test_send_monthly_summary_notifications_sets_timestamp(api_settings):
    device = DeviceFactory()
    template = NotificationTemplateFactory(event_type=EventTypeChoices.MONTHLY_SUMMARY)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + relativedelta(months=1)
    tasks.send_monthly_summary_notifications(now)
    log_entries = list(NotificationLogEntry.objects.all())
    assert len(log_entries) == 1
    assert log_entries[0].device == device
    assert log_entries[0].template == template
    assert log_entries[0].sent_at == now


@responses.activate
def test_send_monthly_summary_notifications_sends_notification(api_settings):
    device = DeviceFactory()
    template = NotificationTemplateFactory(event_type=EventTypeChoices.MONTHLY_SUMMARY)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + relativedelta(months=1)
    tasks.send_monthly_summary_notifications(now)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == API_URL
    expected_body = {
        'uuids': [str(device.uuid)],
        'titleEn': template.render('title', 'en'),
        'titleFi': template.render('title', 'fi'),
        'contentEn': template.render('body', 'en'),
        'contentFi': template.render('body', 'fi'),
    }
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == expected_body
