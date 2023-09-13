from django.utils.timezone import make_aware, utc
from factory import SubFactory
from factory.django import DjangoModelFactory
from datetime import datetime
from trips.tests.factories import DeviceFactory
from freezegun import freeze_time

class SurveyInfoFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.SurveyInfo'
    start_day = '2023-07-15'
    end_day= '2023-07-18'
    days = 3
    max_back_question = 3
    description = 'test Survey'
    id=2

class QuestionsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Questions'
    q_id = 1
    question_data = {'x': 5, 'y': 6}
    question_type = 'test'
    is_use = True
    description = 'questions for test survey'

class ParticipantsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Partisipants'
    device = SubFactory(DeviceFactory)
    survey_info = SubFactory(SurveyInfoFactory)
    start_date = '2023-7-15'
    end_date = '2023-7-18'
    participants_approved = 'No'
    back_question_answers = {'x': 5, 'y': 6}
    feeling_question_answers = {'x': 5, 'y': 6}
    id=2

class DayInfoFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.DayInfo'
    participant = SubFactory(ParticipantsFactory)
    date = make_aware(datetime(2023,7,15),utc)
    poll_approved = 'No'

class LotteryFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Lottery'
    user_name = 'testUser'
    user_email = 'test@mail.com'

@freeze_time("2023-07-15")
class TripsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Trips'
    partisipants = SubFactory(ParticipantsFactory)
    start_time = "2023-07-15T20:59:40"
    end_time = "2023-07-15T23:59:45"
    original_trip = True
    deleted = False
    t_id = 1

@freeze_time("2023-07-15")
class LegsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Legs'
    trip = SubFactory(TripsFactory)
    start_time = "2023-07-15T20:59:40"
    end_time = "2023-07-15T23:59:40"
 #   start_loc = '0101000020E6100000731074B4AA0738405523168CA5C24E40'
 #   end_loc = '0101000020E610000048A5D8D13806384067FA25E2ADC24E40'
    trip_length = 1860.702302423133
    carbon_footprint = 9303.511512115665
    nr_passengers = 1
    transport_mode = 'walking'
    original_leg = True
    deleted = False
    l_id = 1
