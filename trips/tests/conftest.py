import pytest

from budget.models import EmissionBudgetLevel
from poll.models import SurveyInfo, Partisipants, DayInfo, Trips, Legs
from django.utils.timezone import make_aware, utc
from datetime import datetime
from freezegun import freeze_time

@pytest.fixture(autouse=True)
def emission_budget_level_bronze():
    return EmissionBudgetLevel.objects.create(identifier='bronze',
                                              carbon_footprint=30,
                                              year=2020)


@pytest.fixture(autouse=True)
def survey():
    return SurveyInfo.objects.create(start_day='2023-7-15',
                                     end_day='2023-7-18',
                                     days=3,
                                     max_back_question=3,
                                     description='test Survey',
                                     id=2)


@pytest.fixture
def partisipants(survey, device):
    return Partisipants.objects.create(start_date='2023-07-15',
                                       end_date='2023-07-18',
                                       device = device,
                                       survey_info=survey,
                                       approved= False,
                                       back_question_answers = {'x': 5, 'y': 6},
                                       feeling_question_answers = {'x': 5, 'y': 6},
                                       id=2)

@pytest.fixture
def day_info(partisipants):
    return DayInfo.objects.create(partisipant=partisipants,
                                  date='2023-07-15',
                                  approved=False,
                                  id=1)

#@pytest.fixture
#def day_info(partisipants):
#    return DayInfo.objects.create(partisipant=partisipants,
#                                  date='2023-07-16',
#                                  approved=False,
#                                  id=2)
#
#@pytest.fixture
#def day_info(partisipants):
#    return DayInfo.objects.create(partisipant=partisipants,
#                                  date='2023-07-17',
#                                  approved=False,
#                                  id=3)

@freeze_time("2023-07-15")
@pytest.fixture
def survey_trip(partisipants):
    return Trips.objects.create(partisipant=partisipants,
                                start_time="2023-07-15T20:59:40+00",
                                end_time="2023-07-15T23:59:45+00",
                                original_trip = True,
                                deleted = False,
                                purpose="tyo",
                                start_municipality="Tampere",
                                end_municipality="Tampere",
                                approved=False,
                                id=1)


@freeze_time("2023-07-15")
@pytest.fixture
def survey_trip2(partisipants):
    return Trips.objects.create(partisipant=partisipants,
                                start_time="2023-07-15T20:59:40+00",
                                end_time="2023-07-15T23:59:45+00",
                                original_trip = True,
                                deleted = False,
                                purpose="tyo",
                                start_municipality="Tampere",
                                end_municipality="Tampere",
                                approved=False,
                                id=2)

@freeze_time("2023-07-15")
@pytest.fixture
def survey_leg(survey_trip):
    return Legs.objects.create(trip=survey_trip,
                               start_time="2023-07-15T20:59:40+00",
                               end_time="2023-07-15T21:55:45+00",
                               trip_length=1860.702302423133,
                               carbon_footprint=9303.511512115665,
                               start_loc='0101000020E6100000731074B4AA0738405523168CA5C24E40',
                               end_loc='0101000020E610000048A5D8D13806384067FA25E2ADC24E40',
                               nr_passengers=1,
                               transport_mode='walking',
                               original_leg=True,
                               deleted=False,
                               id=1)

@freeze_time("2023-07-15")
@pytest.fixture
def survey_leg2(survey_trip):
    return Legs.objects.create(trip=survey_trip,
                               start_time="2023-07-15T21:59:40+00",
                               end_time="2023-07-15T22:59:45+00",
                               trip_length=1860.702302423133,
                               carbon_footprint=9303.511512115665,
                               start_loc='0101000020E6100000731074B4AA0738405523168CA5C24E40',
                               end_loc='0101000020E610000048A5D8D13806384067FA25E2ADC24E40',
                               nr_passengers=1,
                               transport_mode='walking',
                               original_leg=True,
                               deleted=False,
                               id=2)