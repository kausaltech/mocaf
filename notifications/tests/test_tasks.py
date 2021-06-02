import datetime
import pytest

from trips.tests.factories import DeviceFactory
from notifications import tasks

pytestmark = pytest.mark.django_db


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


def test_send_welcome_notifications_sets_flag(device):
    today = device.created_at + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(today)
    device.refresh_from_db()
    assert device.welcome_notification_sent


def test_send_welcome_notifications_sends_notification(device):
    today = device.created_at + datetime.timedelta(days=1)
    tasks.send_welcome_notifications(today)
    # TODO
