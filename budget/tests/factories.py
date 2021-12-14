from datetime import date
from factory import LazyAttribute, Sequence, SubFactory
from factory.django import DjangoModelFactory

from trips.tests.factories import DeviceFactory


class EmissionBudgetLevelFactory(DjangoModelFactory):
    class Meta:
        model = 'budget.EmissionBudgetLevel'

    identifier = Sequence(lambda i: f'budget_level{i}')
    carbon_footprint = 123
    year = 2020


class PrizeFactory(DjangoModelFactory):
    class Meta:
        model = 'budget.Prize'

    device = SubFactory(DeviceFactory)
    budget_level = SubFactory(EmissionBudgetLevelFactory)
    prize_month_start = LazyAttribute(lambda f: f.device.created_at.replace(day=1))


class DeviceDailyCarbonFootprintFactory(DjangoModelFactory):
    class Meta:
        model = 'budget.DeviceDailyCarbonFootprint'

    device = SubFactory(DeviceFactory)
    date = date(2020, 1, 1)
    carbon_footprint = 123.0
    average_footprint_used = False
