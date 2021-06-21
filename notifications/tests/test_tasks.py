import datetime
import json
import pytest
import responses
from dateutil.relativedelta import relativedelta
from django.utils.timezone import make_aware, utc

from budget.models import EmissionBudgetLevel
from trips.tests.factories import DeviceFactory, LegFactory
from notifications.tasks import (
    MonthlySummaryBronzeNotificationTask, MonthlySummaryGoldNotificationTask, MonthlySummarySilverNotificationTask,
    NoRecentTripsNotificationTask, WelcomeNotificationTask, send_notifications
)
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


def test_welcome_notification_recipients():
    device = DeviceFactory()
    now = device.created_at + datetime.timedelta(days=1)
    task = WelcomeNotificationTask(now)
    result = list(task.recipients())
    assert result == [device]


def test_welcome_notification_recipients_already_sent():
    device = DeviceFactory()
    NotificationLogEntryFactory(device=device,
                                template__event_type=EventTypeChoices.WELCOME_MESSAGE)
    now = device.created_at + datetime.timedelta(days=1)
    task = WelcomeNotificationTask(now)
    result = list(task.recipients())
    assert result == []


def test_welcome_notification_recipients_too_old():
    device = DeviceFactory()
    now = device.created_at + datetime.timedelta(days=2)
    task = WelcomeNotificationTask(now)
    result = list(task.recipients())
    assert result == []


@responses.activate
def test_send_welcome_notifications_records_sending(api_settings):
    device = DeviceFactory()
    template = NotificationTemplateFactory()
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + datetime.timedelta(days=1)
    send_notifications(task_class=WelcomeNotificationTask, now=now)
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
    send_notifications(task_class=WelcomeNotificationTask, now=now)
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


@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
def test_monthly_summary_notification_average_footprint(task_class):
    # FIXME: This partly duplicates the fixture emission_budget_level_bronze. Think about something better.
    EmissionBudgetLevel.objects.create(identifier='bronze',
                                       carbon_footprint=0,
                                       year=2020)
    device1 = DeviceFactory()
    device2 = DeviceFactory()
    LegFactory(trip__device=device1, carbon_footprint=1000)
    LegFactory(trip__device=device2, carbon_footprint=3000)
    now = device1.created_at + relativedelta(months=1)
    task = task_class(now)
    assert task.average_footprint == 2.0


@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
def test_monthly_summary_notification_recipients_no_prior_summary(task_class, emission_budget_level_bronze):
    device = DeviceFactory()
    now = device.created_at + relativedelta(months=1)
    task = task_class(now)
    result = list(task.recipients())
    assert result == [device]


@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
@pytest.mark.parametrize('now', [
    datetime.datetime(2020, 3, 1),
    datetime.datetime(2020, 3, 15),
    datetime.datetime(2020, 3, 31),
])
@pytest.mark.parametrize('last_notification_sent_at', [
    datetime.datetime(2020, 2, 1),  # beginning of last month
    datetime.datetime(2020, 2, 15),  # middle of last month
    datetime.datetime(2020, 2, 29),  # end of last month
    datetime.datetime(2020, 1, 31),  # older than last month
])
def test_monthly_summary_notification_recipients(task_class, now, last_notification_sent_at,
                                                 emission_budget_level_bronze):
    device = DeviceFactory()
    task = task_class(now)
    NotificationLogEntryFactory(device=device,
                                template__event_type=task.event_type,
                                sent_at=make_aware(last_notification_sent_at, utc))
    result = list(task.recipients())
    assert result == [device]


@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
@pytest.mark.parametrize('last_notification_sent_at', [
    datetime.datetime(2020, 3, 1),
    datetime.datetime(2020, 3, 15),
    datetime.datetime(2020, 3, 31),
])
def test_monthly_summary_notification_recipients_already_sent(task_class, last_notification_sent_at,
                                                              emission_budget_level_bronze):
    now = datetime.datetime(2020, 3, 31)
    device = DeviceFactory()
    task = task_class(now)
    NotificationLogEntryFactory(device=device,
                                template__event_type=task.event_type,
                                sent_at=make_aware(last_notification_sent_at, utc))
    result = list(task.recipients())
    assert result == []


@responses.activate
@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
def test_send_monthly_summary_notifications_sets_timestamp(task_class, api_settings, emission_budget_level_bronze):
    device = DeviceFactory()
    template = NotificationTemplateFactory(event_type=task_class.event_type)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + relativedelta(months=1)
    send_notifications(task_class=task_class, now=now)
    log_entries = list(NotificationLogEntry.objects.all())
    assert len(log_entries) == 1
    assert log_entries[0].device == device
    assert log_entries[0].template == template
    assert log_entries[0].sent_at == now


@responses.activate
@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
def test_send_monthly_summary_notifications_sends_notification(task_class, api_settings, emission_budget_level_bronze):
    device = DeviceFactory()
    template = NotificationTemplateFactory(event_type=task_class.event_type)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + relativedelta(months=1)
    send_notifications(task_class=task_class, now=now)
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


@responses.activate
@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
def test_send_monthly_summary_notifications_updates_carbon_footprints(task_class, api_settings,
                                                                      emission_budget_level_bronze):
    # send_monthly_summary_notifications() should call update_daily_carbon_footprint() to be sure that values are
    # substituted for all days on which there is no data.
    device = DeviceFactory()
    NotificationTemplateFactory(event_type=task_class.event_type)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + relativedelta(months=1)
    assert not device.daily_carbon_footprints.exists()
    send_notifications(task_class=task_class, now=now)
    # Gaps (i.e., every day since there are no legs) should have been filled
    assert device.daily_carbon_footprints.exists()


@responses.activate
@pytest.mark.parametrize('task_class', [
    MonthlySummaryGoldNotificationTask,
    MonthlySummarySilverNotificationTask,
    MonthlySummaryBronzeNotificationTask
])
def test_send_monthly_summary_notifications_updates_only_summary_month(task_class, api_settings,
                                                                       emission_budget_level_bronze):
    device = DeviceFactory()
    NotificationTemplateFactory(event_type=task_class.event_type)
    responses.add(responses.POST, API_URL, json=SUCCESS_RESPONSE, status=200)

    now = device.created_at + relativedelta(months=2)
    assert not device.daily_carbon_footprints.exists()
    send_notifications(task_class=task_class, now=now)
    # Only one month of filler data should have been generated
    assert device.daily_carbon_footprints.count() <= 31


def test_no_recent_trips_notification_recipients_exist():
    device = DeviceFactory()
    leg = LegFactory(trip__device=device)
    now = leg.end_time + datetime.timedelta(days=14, seconds=1)
    task = NoRecentTripsNotificationTask(now)
    result = list(task.recipients())
    assert result == [device]


def test_no_recent_trips_notification_recipients_empty():
    leg = LegFactory()
    now = leg.end_time + datetime.timedelta(days=13, seconds=59)
    task = NoRecentTripsNotificationTask(now)
    result = list(task.recipients())
    assert result == []


def test_no_recent_trips_notification_recipients_already_sent():
    device = DeviceFactory()
    leg = LegFactory(trip__device=device)
    sent_at = leg.end_time + datetime.timedelta(days=14, seconds=1)
    NotificationLogEntryFactory(device=device,
                                template__event_type=EventTypeChoices.NO_RECENT_TRIPS,
                                sent_at=sent_at)
    now = sent_at + datetime.timedelta(seconds=1)
    task = NoRecentTripsNotificationTask(now)
    result = list(task.recipients())
    assert result == []
