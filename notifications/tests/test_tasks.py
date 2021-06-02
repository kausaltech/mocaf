import datetime
import json
import pytest
import responses

from trips.tests.factories import DeviceFactory
from notifications import tasks

pytestmark = pytest.mark.django_db

API_URL = 'https://example.com/'


@pytest.fixture
def api_settings(settings):
    settings.GENIEM_NOTIFICATION_API_BASE = API_URL
    settings.GENIEM_NOTIFICATION_API_TOKEN = 'test'


def test_welcome_notification_devices():
    device = DeviceFactory()
    today = device.created_at + datetime.timedelta(days=1)
    result = list(tasks.welcome_notification_devices(today))
    assert result == [device]


def test_welcome_notification_devices_already_sent():
    device = DeviceFactory(welcome_notification_sent=True)
    today = device.created_at + datetime.timedelta(days=1)
    result = list(tasks.welcome_notification_devices(today))
    assert result == []


def test_welcome_notification_devices_too_old():
    device = DeviceFactory()
    today = device.created_at + datetime.timedelta(days=2)
    result = list(tasks.welcome_notification_devices(today))
    assert result == []


@responses.activate
def test_send_welcome_notifications_sets_flag(device, api_settings):
    responses.add(responses.POST, API_URL, json={'todo': 'response'}, status=200)

    today = device.created_at + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(today)
    device.refresh_from_db()
    assert device.welcome_notification_sent


@responses.activate
def test_send_welcome_notifications_sends_notification(device, api_settings):
    responses.add(responses.POST, API_URL, json={'todo': 'response'}, status=200)

    today = device.created_at + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(today)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == API_URL
    expected_body = {
        'uuids': [str(device.uuid)],
        # TODO: title_data, content_data
    }
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == expected_body
