import pytest

from budget.models import EmissionBudgetLevel


@pytest.fixture(autouse=True)
def emission_budget_level_bronze():
    return EmissionBudgetLevel.objects.create(identifier='bronze',
                                              carbon_footprint=30,
                                              year=2020)


@pytest.fixture(autouse=True)
def emission_budget_level_silver():
    return EmissionBudgetLevel.objects.create(identifier='silver',
                                              carbon_footprint=20,
                                              year=2020)


@pytest.fixture(autouse=True)
def emission_budget_level_gold():
    return EmissionBudgetLevel.objects.create(identifier='gold',
                                              carbon_footprint=10,
                                              year=2020)
