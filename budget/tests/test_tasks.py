import datetime
import json
import pytest
import requests
import responses
from dateutil.relativedelta import relativedelta
from django.utils.timezone import make_aware, utc

from budget.enums import EmissionUnit, TimeResolution
from budget.models import EmissionBudgetLevel
from budget.tasks import award_prizes, MonthlyPrizeTask
from budget.tests.factories import EmissionBudgetLevelFactory, PrizeFactory
from trips.tests.factories import DeviceFactory, LegFactory

pytestmark = pytest.mark.django_db

PRIZE_API_URL = 'https://example.com/prizes/'


def budget_level_leg(budget_level, device, date=None):
    if date is None:
        date = device.created_at
    threshold = budget_level.calculate_for_date(date, TimeResolution.MONTH, EmissionUnit.G)
    return LegFactory(
        trip__device=device,
        carbon_footprint=threshold,
        start_time=datetime.datetime.combine(date, datetime.time(), utc),
        end_time=datetime.datetime.combine(date, datetime.time(), utc),
    )


@pytest.fixture
def api_settings(settings):
    settings.GENIEM_PRIZE_API_BASE = PRIZE_API_URL
    settings.GENIEM_PRIZE_API_TOKEN = 'test'


@pytest.fixture
def zero_emission_budget_level():
    return EmissionBudgetLevel(identifier='zero', carbon_footprint=0, year=2020)


@pytest.mark.parametrize('now', [
    datetime.datetime(2020, 4, 1),
    datetime.datetime(2020, 4, 30),
])
@pytest.mark.parametrize('reach_level', [True, False])
def test_monthly_prize_recipients_reach_level(now, zero_emission_budget_level, reach_level):
    device = DeviceFactory()
    budget_level = EmissionBudgetLevelFactory()
    leg = budget_level_leg(budget_level, device, date=datetime.datetime(2020, 3, 1))
    if not reach_level:
        leg.carbon_footprint += 0.001
        leg.save()
    task = MonthlyPrizeTask(budget_level.identifier, now=now, default_emissions=zero_emission_budget_level)
    result = list(task.recipients())
    if reach_level:
        assert result == [device]
    else:
        assert result == []


@pytest.mark.parametrize('reach_next_level', [True, False])
def test_monthly_prize_recipients_reach_next_level(zero_emission_budget_level, reach_next_level):
    now = datetime.datetime(2020, 4, 1)
    device = DeviceFactory()
    budget_level = EmissionBudgetLevelFactory(carbon_footprint=100)
    next_level = EmissionBudgetLevelFactory(carbon_footprint=50)
    leg = budget_level_leg(next_level, device, date=datetime.datetime(2020, 3, 1))
    if not reach_next_level:
        leg.carbon_footprint += 0.001
        leg.save()
    task = MonthlyPrizeTask(
        budget_level.identifier, next_level.identifier, now=now, default_emissions=zero_emission_budget_level
    )
    result = list(task.recipients())
    if reach_next_level:
        assert result == []
    else:
        assert result == [device]


@pytest.mark.parametrize('already_awarded', [False, True])
def test_monthly_prize_recipients_already_awarded(zero_emission_budget_level, already_awarded):
    now = datetime.datetime(2020, 4, 1)
    if already_awarded:
        last_prize_month = datetime.date(2020, 3, 1)
    else:
        last_prize_month = datetime.date(2020, 2, 1)
    device = DeviceFactory()
    budget_level = EmissionBudgetLevelFactory()
    PrizeFactory(device=device, prize_month_start=last_prize_month)
    budget_level_leg(budget_level, device, date=datetime.datetime(2020, 3, 1))
    task = MonthlyPrizeTask(budget_level.identifier, now=now, default_emissions=zero_emission_budget_level)
    result = list(task.recipients())
    if already_awarded:
        assert result == []
    else:
        assert result == [device]


@pytest.mark.parametrize('already_awarded', [False, True])
def test_monthly_prize_recipients_too_few_active_days(zero_emission_budget_level, already_awarded):
    now = datetime.datetime(2020, 4, 1)
    device = DeviceFactory()
    budget_level = EmissionBudgetLevelFactory()
    budget_level_leg(budget_level, device, date=datetime.datetime(2020, 3, 1))
    task = MonthlyPrizeTask(
        budget_level.identifier, now=now, default_emissions=zero_emission_budget_level, min_active_days=2
    )
    result = list(task.recipients())
    assert result == []


@responses.activate
def test_award_prizes_calls_api(api_settings, zero_emission_budget_level):
    now = datetime.datetime(2020, 4, 1)
    device = DeviceFactory()
    budget_level = EmissionBudgetLevelFactory()
    budget_level_leg(budget_level, device, date=datetime.datetime(2020, 3, 1))
    responses.add(responses.POST, PRIZE_API_URL, status=200)
    award_prizes(budget_level.identifier, now=now, default_emissions=zero_emission_budget_level)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == PRIZE_API_URL
    expected_body = [{
        "uuid": str(device.uuid),
        "level": budget_level.identifier,
        "year": 2020,
        "month": 3,
    }]
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == expected_body
