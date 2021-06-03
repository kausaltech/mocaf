import datetime
import json
import pytest
import responses

from trips.tests.factories import DeviceFactory
from notifications import tasks
from notifications.models import EventTypeChoices
from notifications.tests.factories import NotificationTemplateFactory

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
    device = DeviceFactory(welcome_notification_sent=True)
    today = device.created_at.date() + datetime.timedelta(days=1)
    result = list(tasks.welcome_notification_devices(today))
    assert result == []


def test_welcome_notification_devices_too_old():
    device = DeviceFactory()
    today = device.created_at.date() + datetime.timedelta(days=2)
    result = list(tasks.welcome_notification_devices(today))
    assert result == []


@responses.activate
def test_send_welcome_notifications_sets_flag(device, api_settings):
    NotificationTemplateFactory(event_type=EventTypeChoices.WELCOME_MESSAGE)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    today = device.created_at.date() + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(today)
    device.refresh_from_db()
    assert device.welcome_notification_sent


@responses.activate
def test_send_welcome_notifications_sends_notification(device, api_settings):
    template = NotificationTemplateFactory(event_type=EventTypeChoices.WELCOME_MESSAGE)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    today = device.created_at.date() + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(today)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == API_URL
    expected_body = {
        'uuids': [str(device.uuid)],
        'contentEn': template.body_en,
        'contentFi': template.body_fi,
        'titleEn': template.title_en,
        'titleFi': template.title_fi,
    }
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == expected_body


def test_monthly_summary_notification_devices_no_prior_summary():
    device = DeviceFactory()
    month = device.created_at.date().replace(day=1)
    result = list(tasks.monthly_summary_notification_devices(month))
    assert result == [device]


@pytest.mark.parametrize('last_notification_month', [
    datetime.date(2020, 2, 1),  # one month ago
    datetime.date(2020, 1, 1),  # more than one month ago
])
def test_monthly_summary_notification_devices(last_notification_month):
    summary_month = datetime.date(2020, 3, 1)
    device = DeviceFactory(last_summary_notification_month=last_notification_month)
    result = list(tasks.monthly_summary_notification_devices(summary_month))
    assert result == [device]


def test_monthly_summary_notification_devices_already_sent():
    month = datetime.date(2020, 1, 1)
    DeviceFactory(last_summary_notification_month=month)
    result = list(tasks.monthly_summary_notification_devices(month))
    assert result == []


@responses.activate
def test_send_monthly_summary_notifications_sets_timestamp(device, api_settings):
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    today = datetime.date(2020, 2, 1)
    # Send notification for January 2020
    tasks.send_monthly_summary_notifications(today)
    device.refresh_from_db()
    last_month = datetime.date(2020, 1, 1)
    assert device.last_summary_notification_month == last_month


@responses.activate
def test_send_monthly_summary_notifications_sends_notification(device, api_settings):
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    today = datetime.date(2020, 2, 1)
    # Send notification for January 2020
    tasks.send_monthly_summary_notifications(today)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == API_URL
    expected_body = {
        'uuids': [str(device.uuid)],
        'contentEn': template.body_en,
        'contentFi': template.body_fi,
        'titleEn': template.title_en,
        'titleFi': template.title_fi,
    }
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == expected_body
