import datetime
import logging
import random
import statistics
from typing import Any, Dict, List, Optional
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import override
from importlib import import_module
from django.db.models import F

import sentry_sdk

from budget.enums import PrizeLevel, TimeResolution, EmissionUnit
from budget.models import EmissionBudgetLevel
from budget.tasks import MonthlyPrizeTask
from trips.models import Device, DeviceQuerySet
from poll.models import Partisipants
from .engine import NotificationEngine
from .models import EventTypeChoices, NotificationLogEntry, NotificationTemplate

logger = logging.getLogger(__name__)

# Tasks usable in send_notification management command
registered_tasks = []


def register_for_management_command(cls):
    registered_tasks.append(cls)
    return cls


class NotificationTask:
    def __init__(self, event_type, now=None, engine=None, dry_run=False, devices=None, force=False):
        """
        `devices` can be set to a QuerySet smaller than Device.objects.all() to limit the potential recipients.
        If `force` is True, attempt to send the notification to all devices in `devices` (or all if `devices` is not
        set) regardless of whether they qualify for the notification.
        """
        if now is None:
            now = timezone.now()
        if engine is None:
            engine = NotificationEngine()
        if devices is None:
            devices = Device.objects.filter(enabled_at__isnull=False)

        self.event_type = event_type
        self.now = now
        self.engine = engine
        self.dry_run = dry_run
        self.devices = devices
        self.force = force

    def recipients(self):
        """Return the recipient devices for the notifications to be sent at `self.now`."""
        return self.devices

    def contexts(self, device: Device):
        """Return a dict mapping languages to a context for rendering notification templates for the given device."""
        return {language: {} for language, _ in settings.LANGUAGES}

    def get_available_templates(self) -> List[NotificationTemplate]:
        templates = NotificationTemplate.objects.filter(event_type=self.event_type)
        return list(templates)

    def choose_template(self, device: Device, available_templates: List[NotificationTemplate]) -> Optional[NotificationTemplate]:
        """Choose a template to send"""
        try:
            return random.choice(available_templates)
        except IndexError:
            raise Exception(f"There is no notification template of type {self.event_type}.")

    def get_extra_data(self, device: Device, template: NotificationTemplate) -> Optional[Dict[str, Any]]:
        return None

    def send_notifications(self):
        """Send notifications using a randomly chosen template of the proper event type."""
        logger.info(f"Sending {self.event_type} notifications")

        available_templates = self.get_available_templates()
        if not available_templates:
            logger.info("No templates found")
            return

        if self.force:
            recipients = self.devices
        else:
            recipients = self.recipients()
        logger.info(f"Sending notification to {len(recipients)} devices")

        fail_count = 0

        for device in recipients:
            template = self.choose_template(device, available_templates=available_templates)
            if template is None:
                continue

            with transaction.atomic() as _, sentry_sdk.push_scope() as scope:
                scope.set_tag('device', str(device.uuid))
                scope.set_tag('event_type', str(self.event_type))
                scope.set_tag('template_id', template.id)

                contexts = self.contexts(device)
                title = template.render_all_languages('title', contexts)
                content = template.render_all_languages('body', contexts)
                extra_data = self.get_extra_data(device, template)
                if self.dry_run:
                    print(f"Sending notification to {device.uuid}")
                    print("Title:")
                    print(title)
                    print("Content:")
                    print(content)
                    print("Extra data:")
                    print(extra_data)
                    print()
                    continue

                logger.info(f"Sending notification to {device.uuid}")
                # TODO: Send to multiple devices at once (unless context is device-specific) by using a list of all
                # devices as first argument of engine.send_notification()
                send_exception = None
                try:
                    response = self.engine.send_notification([device], title, content, extra_data=extra_data).json()
                except Exception as e:
                    send_exception = e

                if send_exception is not None or not response['ok'] or response['message'] != 'success':
                    fail_count += 1
                    scope.set_context('api-response', response)
                    if send_exception is None:
                        send_exception = Exception("Sending notification failed")
                    sentry_sdk.capture_exception(send_exception)
                    if fail_count > 5:
                        raise Exception("Too many failures in a row, bailing out")
                    continue

                # Success, reset failure count
                fail_count = 0
                NotificationLogEntry.objects.create(device=device, template=template, sent_at=self.now)


@register_for_management_command
class WelcomeNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False, min_active_days=0):
        super().__init__(EventTypeChoices.WELCOME_MESSAGE, now, engine, dry_run, devices, force)

    def recipients(self):
        """Return devices that signed up on the day preceding `self.now`."""
        # Don't send anything to devices that already got a welcome notification
        excluded_devices = (NotificationLogEntry.objects
                            .filter(template__event_type=self.event_type)
                            .values('device'))
        today = self.now.date()
        yesterday = today - datetime.timedelta(days=1)
        return (super().recipients()
                .filter(created_at__date__gte=yesterday)
                .exclude(id__in=excluded_devices))


@register_for_management_command
class TimedNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False, **kwargs):
        super().__init__(EventTypeChoices.TIMED_MESSAGE, now, engine, dry_run, devices, force)

    def get_available_templates(self) -> List[NotificationTemplate]:
        available_templates = list(NotificationTemplate.objects.filter(
            event_type=self.event_type,
            send_on=self.now.date()
        ).prefetch_related('groups'))
        return available_templates

    def choose_template(self, device: Device, available_templates: List[NotificationTemplate]) -> Optional[NotificationTemplate]:
        for template in available_templates:
            tmp_groups = template.groups.all()
            if not tmp_groups:
                return template
            dev_groups = device.groups.all()
            for grp in tmp_groups:
                if grp in dev_groups:
                    return template
        return None

    def recipients(self):
        devices = super().recipients()
        if self.force:
            return devices

        templates = self.get_available_templates()
        possible_groups = set()
        for t in templates:
            t_grps = t.groups.all()
            if not t_grps:
                possible_groups.clear()
                break
            possible_groups.update(list(t_grps))

        if possible_groups:
            devices = devices.filter(groups__in=possible_groups)

        earlier_recipients = (
            NotificationLogEntry.objects.filter(template__event_type=self.event_type)
            .filter(sent_at__date__gte=self.now.date())
            .values('device')
        )
        devices = devices.exclude(id__in=earlier_recipients)
        return devices


class MonthlySummaryNotificationTask(NotificationTask):
    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        """
        If `restrict_average` is True, consider only devices in `devices` for the average footprint and only regenerate
        the carbon footprints for these. (Useful for testing since regenerating footprints is expensive.)
        `min_active_days` is the number of days of the relevant month that the device must have been active in order to
        receive a notification.
        """
        if getattr(self, 'event_type', None) is None:
            raise AttributeError("MonthlySummaryNotificationTask subclass must define event_type")

        super().__init__(self.event_type, now, engine, dry_run, devices, force)
        self.min_active_days = min_active_days

        one_month_ago = self.now - relativedelta(months=1)
        start_date = one_month_ago.date().replace(day=1)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = self.now.date().replace(day=1) - datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        self.summary_month_start = start_date
        self.summary_month_end = end_date

        # Update carbon footprints of all relevant devices to make sure there are no gaps on days without data
        if restrict_average:
            qs = devices
        else:
            qs = Device.objects.all()

        device_universe = qs.has_trips_during(start_date, end_date)

        for device in device_universe:
            # We shouldn't call this if dry_run is True, but it probably doesn't break things if we do
            device.update_daily_carbon_footprint(start_datetime, end_datetime, default_emissions)
        self.footprints = {device: device.monthly_carbon_footprint(start_date) for device in device_universe}
        self.average_footprint = None
        if self.footprints:
            self.average_footprint = statistics.mean(self.footprints.values())
        self.num_active_days = {device: device.num_active_days(start_date) for device in device_universe}

    def recipients(self):
        """Return devices that should receive a summary for the calendar month preceding the one of `self.now`."""
        today = self.now.date()
        this_month = today.replace(day=1)
        # Don't send anything to devices that already got a summary notification this month
        earlier_recipients = (NotificationLogEntry.objects
                              .filter(template__event_type=self.event_type)
                              .filter(sent_at__date__gte=this_month)
                              .values('device'))

        eligible_footprint_devices = [
            dev.id for dev, footprint in self.footprints.items() if self.footprint_eligible(footprint)
        ]

        sufficiently_active_devices = [
            dev.id for dev, num_active_days in self.num_active_days.items() if num_active_days >= self.min_active_days
        ]

        return (super().recipients()
                .filter(id__in=eligible_footprint_devices)
                .filter(id__in=sufficiently_active_devices)
                .exclude(id__in=earlier_recipients))

    def contexts(self, device: Device):
        def rounded_float(f):
            return '%s' % int(float('%.3g' % f))
        contexts = super().contexts(device)
        for language, context in contexts.items():
            context['average_carbon_footprint'] = rounded_float(self.average_footprint)
            # FIXME: The commented-out line reports the footprint as used for prize determination. However, in the app,
            # device.get_carbon_footprint_summary() is used for the footprint and this does not fill in "default
            # emissions" for days without any data. So the numbers differ. Ideally, the app should display the corrected
            # footprint (i.e., containing the filled-in value), but it does not for now.
            # context['carbon_footprint'] = rounded_float(self.footprints[device])
            footprint_summary = device.get_trip_summary(
                self.summary_month_start,
                self.summary_month_end,
                time_resolution=TimeResolution.MONTH,
                units=EmissionUnit.KG,
            )
            if not footprint_summary:
                carbon_footprint = 0.0
            else:
                assert len(footprint_summary) == 1
                footprint_summary = footprint_summary[0]
                assert footprint_summary['date'] == self.summary_month_start
                carbon_footprint = footprint_summary['carbon_footprint']
            context['carbon_footprint'] = rounded_float(carbon_footprint)
            with override(language):
                context['month'] = date_format(self.summary_month_start, 'F')
        return contexts

    def footprint_eligible(self, footprint):
        """Return true iff devices with the given footprint are eligible for getting the notification."""
        return True


@register_for_management_command
class MonthlySummaryGoldNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_GOLD

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
        )
        self.gold_level = EmissionBudgetLevel.objects.get(identifier='gold', year=self.summary_month_start.year)
        self.gold_threshold = self.gold_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        return footprint <= self.gold_threshold


@register_for_management_command
class MonthlySummarySilverNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_SILVER

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
        )
        self.silver_level = EmissionBudgetLevel.objects.get(identifier='silver', year=self.summary_month_start.year)
        self.gold_level = EmissionBudgetLevel.objects.get(identifier='gold', year=self.summary_month_start.year)
        self.silver_threshold = self.silver_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )
        self.gold_threshold = self.gold_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        return footprint <= self.silver_threshold and footprint > self.gold_threshold


@register_for_management_command
class MonthlySummaryBronzeOrWorseNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_BRONZE_OR_WORSE

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
        )
        self.bronze_level = EmissionBudgetLevel.objects.get(identifier='bronze', year=self.summary_month_start.year)
        self.silver_level = EmissionBudgetLevel.objects.get(identifier='silver', year=self.summary_month_start.year)
        self.bronze_threshold = self.bronze_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )
        self.silver_threshold = self.silver_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        # Anything worse than silver gets a notification even if not within bronze level
        return footprint > self.silver_threshold


@register_for_management_command
class MonthlySummaryBronzeNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_BRONZE

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
        )
        self.bronze_level = EmissionBudgetLevel.objects.get(identifier='bronze', year=self.summary_month_start.year)
        self.silver_level = EmissionBudgetLevel.objects.get(identifier='silver', year=self.summary_month_start.year)
        self.bronze_threshold = self.bronze_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )
        self.silver_threshold = self.silver_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        # Anything worse than silver gets a notification even if not within bronze level
        return footprint > self.silver_threshold and footprint <= self.bronze_threshold


@register_for_management_command
class MonthlySummaryNoLevelNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_NO_LEVEL_REACHED

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
        )
        self.bronze_level = EmissionBudgetLevel.objects.get(identifier='bronze', year=self.summary_month_start.year)
        self.bronze_threshold = self.bronze_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        # Anything worse than silver gets a notification even if not within bronze level
        return footprint > self.bronze_threshold


@register_for_management_command
class HealthSummaryNotificationTask(NotificationTask):
    time_period = TimeResolution.WEEK
    event_types = (
        EventTypeChoices.HEALTH_SUMMARY_GOLD,
        EventTypeChoices.HEALTH_SUMMARY_SILVER,
        EventTypeChoices.HEALTH_SUMMARY_BRONZE,
        EventTypeChoices.HEALTH_SUMMARY_NO_LEVEL_REACHED,
        EventTypeChoices.HEALTH_SUMMARY_NO_DATA,
    )

    def __init__(
        self, now=None, engine=None, dry_run=False, devices: Optional[QuerySet[Device]] = None,
        force=False, **kwargs
    ):
        super().__init__(EventTypeChoices.HEALTH_SUMMARY_GOLD, now, engine, dry_run, devices, force)

        last_week = self.now - datetime.timedelta(days=7)
        # Start on first day of the week
        start_date = last_week.date()

        assert self.time_period == TimeResolution.WEEK
        start_date -= datetime.timedelta(days=start_date.weekday())
        end_date = start_date + datetime.timedelta(days=6)
        self.summary_start = start_date
        self.summary_end = end_date

        templates = self.get_available_templates()
        if len(templates) == 0:
            logger.info('No templates for health summaries for today')
            return

        active_devices: DeviceQuerySet = Device.objects.has_trips_during(start_date, end_date)
        logger.info('Calculating trip summaries for %d devices between %s and %s',
            len(active_devices), start_date.isoformat(), end_date.isoformat()
        )
        self.summaries = {
            device: device.get_trip_summary(
                start_date, end_date, time_resolution=self.time_period, ranking='health'
            ) for device in active_devices
        }
        total_devices = len(active_devices) or 1
        walk = 0
        bicycle = 0
        for dev_summary in self.summaries.values():
            assert len(dev_summary) == 1
            s = dev_summary[0]
            assert s['date'] == start_date
            walk += s['walk_mins']
            bicycle += s['bicycle_mins']
        self.average_walk_mins = walk / total_devices
        self.average_bicycle_mins = bicycle / total_devices
        logger.info('Average of %.1f mins walking, %.1f mins bicycling',
            self.average_walk_mins, self.average_bicycle_mins
        )

    def get_available_templates(self) -> List[NotificationTemplate]:
        return list(NotificationTemplate.objects.filter(
            event_type__in=self.event_types, send_on=self.now.date()
        ))

    def choose_template(self, device: Device, available_templates: List[NotificationTemplate]) -> Optional[NotificationTemplate]:
        PRIZE_LEVEL_EVENTS = {
            PrizeLevel.GOLD: EventTypeChoices.HEALTH_SUMMARY_GOLD,
            PrizeLevel.SILVER: EventTypeChoices.HEALTH_SUMMARY_SILVER,
            PrizeLevel.BRONZE: EventTypeChoices.HEALTH_SUMMARY_BRONZE,
        }
        summary = self.summaries[device]
        s = summary[0]
        prize_level = s['health_prize_level']
        if not prize_level:
            if not s['walk_mins'] and not s['bicycle_mins']:
                event_type = EventTypeChoices.HEALTH_SUMMARY_NO_DATA
            else:
                event_type = EventTypeChoices.HEALTH_SUMMARY_NO_LEVEL_REACHED
        else:
            event_type = PRIZE_LEVEL_EVENTS[prize_level]

        tlist = [t for t in available_templates if t.event_type == event_type]
        if not tlist:
            return None
        return random.choice(tlist)

    def recipients(self):
        """Return devices that should receive the summary."""
        today = self.now.date()
        devices = self.devices.filter(health_impact_enabled=True).has_trips_during(self.summary_start, self.summary_end)
        earlier_recipients = (
            NotificationLogEntry.objects.filter(template__event_type__in=self.event_types)
            .filter(sent_at__date__gte=today)
            .values('device')
        )
        return devices.exclude(id__in=earlier_recipients)

    def contexts(self, device: Device):
        contexts = super().contexts(device)

        def format_float(f: float) -> str:
            return '%.0f' % f

        summary = self.summaries[device][0]
        for language, context in contexts.items():
            assert summary['date'] == self.summary_start
            with override(language):
                context['bicycle_mins'] = format_float(summary['bicycle_mins'])
                context['walk_mins'] = format_float(summary['walk_mins'])
                context['bicycle_walk_mins'] = format_float(summary['walk_mins'] + summary['bicycle_mins'])
                context['average_bicycle_mins'] = format_float(self.average_bicycle_mins)
                context['average_walk_mins'] = format_float(self.average_walk_mins)
                context['average_bicycle_walk_mins'] = format_float(self.average_bicycle_mins + self.average_walk_mins)
        return contexts

    def get_extra_data(self, device: Device, template: NotificationTemplate) -> Optional[Dict[str, Any]]:
        return dict(actionType='health_impact_previous_week')


@register_for_management_command
class NoRecentTripsNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False, min_active_days=0):
        super().__init__(EventTypeChoices.NO_RECENT_TRIPS, now, engine, dry_run, devices, force)

    def recipients(self):
        """Return devices that have not had any trips in 14 days until `self.now`."""
        # Don't send anything to devices that already got a no-recent-trips notification in the last 30 days
        avoid_duplicates_after = self.now - datetime.timedelta(days=30)
        already_notified_devices = (NotificationLogEntry.objects
                                    .filter(template__event_type=self.event_type)
                                    .filter(sent_at__gte=avoid_duplicates_after)
                                    .values('device'))
        inactivity_threshold = self.now - datetime.timedelta(days=14)
        devices_with_recent_trips = (Device.objects
                                     .filter(trips__legs__end_time__gte=inactivity_threshold)
                                     .values('id'))
        return (super().recipients()
                .exclude(id__in=devices_with_recent_trips)
                .exclude(id__in=already_notified_devices))


@register_for_management_command
class NoTripsTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False, min_active_days=0):
        super().__init__(EventTypeChoices.NO_TRIPS, now, engine, dry_run, devices, force)

    def recipients(self):
        """Return devices that have not had any trips between 2 days after register."""
        already_notified_devices = (NotificationLogEntry.objects
                                    .filter(template__event_type=self.event_type)
                                    .filter(sent_at__gte=F("poll_partisipants__registered_to_survey_at" + datetime.timedelta(days=2)))
                                    .values('device'))
        not_in_survey = (Device.objects
                         .filter(survey_enabled= not True)
                         .values('id'))
        
        has_survey_trips = (Partisipants.objects
                            .filter(poll_trips__poll_legs__start_time__gte=F("registered_to_survey_at"))
                            .values('device'))
        has_trips = (Partisipants.objects
                    .filter(trips__legs__start_time__gte=F("registered_to_survey_at"))
                    .values('device'))
        return (super().recipients()
                .exclude(id__in=has_survey_trips)
                .exclude(id__in=already_notified_devices)
                .exclude(id__in=has_trips)
                .exclude(id__in=not_in_survey))

@register_for_management_command
class SurveyNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False, min_active_days=0):
        super().__init__(EventTypeChoices.PART_OF_SURVEY, now, engine, dry_run, devices, force)

    def recipients(self):
        already_notified_devices = (NotificationLogEntry.objects
                                    .filter(template__event_type=self.event_type)
                                    .values('device'))
        not_in_survey = (Device.objects
                         .filter(survey_enabled= not True)
                         .values('id'))
        return (super().recipients()
                .exclude(id__in=already_notified_devices)
                .exclude(id__in=not_in_survey))
    
    
@register_for_management_command
class SurveyStartNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False, min_active_days=0):
        super().__init__(EventTypeChoices.SURVEY_START, now, engine, dry_run, devices, force)

    def recipients(self):
        already_notified_devices = (NotificationLogEntry.objects
                                    .filter(template__event_type=self.event_type)
                                    .values('device'))
        not_in_survey = (Device.objects
                         .filter(survey_enabled= not True)
                         .values('id'))
        devices_with_survey_not_starting = (Device.objects
                                     .filter(survey_enabled=True)
                                     .filter(poll_partisipants__start_date__gt=self.now)
                                     .values('id'))
        return (super().recipients()
                .exclude(id__in=devices_with_survey_not_starting)
                .exclude(id__in=already_notified_devices)
                .exclude(id__in=not_in_survey))

@shared_task
def send_notifications(task_class, devices=None, **kwargs):
    if isinstance(task_class, str):
        parts = task_class.split('.')
        class_name = parts.pop(-1)
        module = import_module('.'.join(parts))
        task_class = getattr(module, class_name)
    task = task_class(devices=devices, **kwargs)
    task.send_notifications()


@shared_task
def send_health_summary_notifications(devices=None, **kwargs):
    HealthSummaryNotificationTask(devices=devices, **kwargs).send_notifications()


@shared_task
def award_prizes_and_send_notifications(devices=None, **kwargs):
    MonthlyPrizeTask('bronze', 'silver', devices=devices, **kwargs).award_prizes()
    MonthlyPrizeTask('silver', 'gold', devices=devices, **kwargs).award_prizes()
    MonthlyPrizeTask('gold', devices=devices, **kwargs).award_prizes()
    MonthlySummaryNoLevelNotificationTask(devices=devices, **kwargs).send_notifications()
    MonthlySummaryBronzeNotificationTask(devices=devices, **kwargs).send_notifications()
    MonthlySummarySilverNotificationTask(devices=devices, **kwargs).send_notifications()
    MonthlySummaryGoldNotificationTask(devices=devices, **kwargs).send_notifications()
