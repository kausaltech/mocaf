from django.utils.timezone import make_aware, utc
from factory import SubFactory
from factory.django import DjangoModelFactory
from datetime import datetime
from trips.tests.factories import DeviceFactory

class SurveyInfoFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.SurveyInfo'
    start_day = make_aware(datetime(2023, 7, 15), utc)
    end_day= make_aware(datetime(2023, 7, 18), utc)
    days = 3
    max_back_question = 3
    description = 'test survey'

class QuestionsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Questions'
    question_data = {}
    question_type = 'test'
    is_used = True
    description = 'questions for test survey'

class ParticipantsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Partisipants'
    device = SubFactory(DeviceFactory)
    survey_info = SubFactory(SurveyInfoFactory)
    start_date = make_aware(datetime(2023,7,15),utc)
    end_date = make_aware(datetime(2023,7,18),utc)
    participants_approved = 'No'
    back_question_answers = {}
    feeling_question_answers = {}

class DayInfoFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.DayInfo'
    participants = SubFactory(ParticipantsFactory)
    date = make_aware(datetime(2023,7,15),utc)
    poll_approved = 'No'

class LotteryFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Lottery'
    user_name = 'testUser'
    user_email = 'test@mail.fi'

class TripsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Trips'
    partisipants = SubFactory(ParticipantsFactory)
    start_time = make_aware(datetime(2023,7,15,12),utc)
    end_time = make_aware(datetime(2023,7,15,12,20),utc)
    original_trip = True
    deleted = False

class LegsFactory(DjangoModelFactory):
    class Meta:
        model = 'poll.Legs'
    trip = SubFactory(TripsFactory)
    start_time = make_aware(datetime(2023,7,15,12),utc)
    end_time = make_aware(datetime(2023,7,15,12,20),utc)
    start_loc = '0101000020E6100000731074B4AA0738405523168CA5C24E40'
    end_loc = '0101000020E610000048A5D8D13806384067FA25E2ADC24E40'
    trip_length = 1860.702302423133
    carbon_footprint = 9303.511512115665
    nr_passengers = 1
    transport_mode = 'walking'
    original_leg = True
    deleted = False
