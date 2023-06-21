import pytest

from budget.models import EmissionBudgetLevel


@pytest.fixture(autouse=True)
def emission_budget_level_bronze():
    return EmissionBudgetLevel.objects.create(identifier='bronze',
                                              carbon_footprint=30,
                                              year=2020)
