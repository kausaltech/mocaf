import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.utils.timezone import make_aware, utc

from trips.tests.factories import DeviceFactory, LegFactory, TripFactory
from poll.tests.factories import (ParticipantsFactory, QuestionsFactory, LotteryFactory, LegsFactory, TripsFactory, SurveyInfoFactory)
from trips.models import Device, Leg, Trip
from freezegun import freeze_time

pytestmark = pytest.mark.django_db


def test_trip_node(graphql_client_query_data, uuid, token, trip):
    leg = LegFactory(trip=trip)
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
            deletedAt
            legs {
              __typename
              id
            }
            startTime
            endTime
            carbonFootprint
            length
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'trips': [{
            'id': str(trip.id),
            'deletedAt': None if trip.deleted_at is None else trip.deleted_at.isoformat(),
            'legs': [{
                '__typename': 'Leg',
                'id': str(leg.id),
            }],
            'startTime': leg.start_time.isoformat(),
            'endTime': leg.end_time.isoformat(),
            'carbonFootprint': trip.carbon_footprint,
            'length': trip.length,
        }]
    }
    assert data == expected


def test_leg_node(graphql_client_query_data, uuid, token, trip):
    leg = LegFactory(trip=trip)
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            legs {
              id
              mode {
                __typename
                id
              }
              modeConfidence
              startTime
              endTime
              startLoc
              endLoc
              length
              carbonFootprint
              nrPassengers
              deletedAt
              canUpdate
            }
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'trips': [{
            'legs': [{
                'id': str(leg.id),
                'mode': {
                    '__typename': 'TransportMode',
                    'id': str(leg.mode.id),
                },
                'modeConfidence': leg.mode_confidence,
                'startTime': leg.start_time.isoformat(),
                'endTime': leg.end_time.isoformat(),
                'startLoc': {
                    'type': 'Point',
                    'coordinates': [c for c in leg.start_loc],
                },
                'endLoc': {
                    'type': 'Point',
                    'coordinates': [c for c in leg.end_loc],
                },
                'length': leg.length,
                'carbonFootprint': leg.carbon_footprint,
                'nrPassengers': leg.nr_passengers,
                'deletedAt': leg.deleted_at,
                'canUpdate': leg.can_user_update(),
            }],
        }]
    }
    assert data == expected


def test_only_list_own_trips(graphql_client_query_data, uuid, token, trip):
    LegFactory(trip=trip)
    other_device = DeviceFactory()
    assert other_device.uuid != uuid
    other_trip = TripFactory(device=other_device)
    LegFactory(trip=other_trip)
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'trips': [{
            'id': str(trip.id),
        }]
    }
    assert data == expected


def test_device_directive_missing_token(graphql_client_query, contains_error, uuid, trip):
    response = graphql_client_query(
        '''
        query($uuid: String!)
        @device(uuid: $uuid)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Token required')


def test_device_directive_missing_uuid(graphql_client_query, contains_error, uuid, token, trip):
    response = graphql_client_query(
        '''
        query($token: String!)
        @device(token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'token': token}
    )
    assert contains_error(response,
                          message='Directive "device" argument "uuid" of type "String!" is required but not provided.')


def test_device_directive_mocaf_not_enabled(graphql_client_query, contains_error):
    device = DeviceFactory(enable_after_creation=False)
    assert device.token is None
    token = '12345678-1234-1234-1234-123456789012'
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Invalid token')


def test_device_directive_invalid_token(graphql_client_query, contains_error, uuid, token, trip):
    invalid_token = '12345678-1234-1234-1234-123456789012'
    assert token != invalid_token
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': invalid_token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Invalid token')


def test_device_directive_mocaf_disabled(graphql_client_query, disable_mocaf, contains_error, uuid, token, trip):
    assert trip.device
    disable_mocaf(uuid, token)
    assert not trip.device.enabled
    response = graphql_client_query(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips {
            id
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert contains_error(response, code='AUTH_FAILED', message='Mocaf disabled')


def test_enable_mocaf_without_token(graphql_client_query_data, enable_mocaf):
    device = DeviceFactory(enable_after_creation=False)
    assert not device.enabled
    assert device.token is None
    token = enable_mocaf(device.uuid)
    assert token
    device.refresh_from_db()
    assert device.enabled
    assert device.token == token


def test_enable_mocaf_with_token(disable_mocaf, enable_mocaf):
    device = DeviceFactory(enable_after_creation=False)
    # To have a token, we need to have enabled Mocaf at least once. To enable Mocaf again, it must be disabled before.
    token = enable_mocaf(device.uuid)
    disable_mocaf(device.uuid, token)
    device.refresh_from_db()
    assert not device.enabled
    assert device.token == token
    enable_result = enable_mocaf(device.uuid, token)
    assert enable_result is None
    device.refresh_from_db()
    assert device.enabled
    assert device.token == token


def test_enable_mocaf_device_directive_missing(graphql_client_query, contains_error, uuid, token):
    # We want enableMocaf to complain when the device already has a token but it's not supplied via the @device
    # directive.
    response = graphql_client_query(
        '''
        mutation($uuid: String!) {
          enableMocaf(uuid: $uuid) {
            ok
            token
          }
        }
        ''',
        variables={'uuid': uuid}
    )
    assert contains_error(response, message='Device exists, specify token with the @device directive')


def test_enable_mocaf_creates_device(graphql_client_query_data):
    uuid = '12345678-9abc-def0-1234-567890123456'
    assert not Device.objects.filter(uuid=uuid).exists()
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!) {
          enableMocaf(uuid: $uuid) {
            ok
            token
          }
        }
        ''',
        variables={'uuid': str(uuid)}
    )
    assert data['enableMocaf']['ok']
    assert data['enableMocaf']['token']
    assert Device.objects.filter(uuid=uuid).exists()


@pytest.mark.parametrize('reverse', [False, True])
def test_trips_ordered_by_time(graphql_client_query_data, reverse):
    if reverse:
        start1, start2 = make_aware(datetime(2020, 3, 2), utc), make_aware(datetime(2020, 3, 1), utc)
    else:
        start1, start2 = make_aware(datetime(2020, 3, 1), utc), make_aware(datetime(2020, 3, 2), utc)
    end1 = start1 + relativedelta(hours=1)
    end2 = start2 + relativedelta(hours=1)

    device = DeviceFactory()
    trip1 = TripFactory(device=device)
    LegFactory(trip=trip1, start_time=start1, end_time=end1)
    trip2 = TripFactory(device=device)
    LegFactory(trip=trip2, start_time=start2, end_time=end2)

    response = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          trips(orderBy: "startTime") {
            id
          }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    if reverse:
        expected_order = [trip2, trip1]
    else:
        expected_order = [trip1, trip2]
    assert response == {
        'trips': [{'id': str(trip.id)} for trip in expected_order]
    }


def test_update_leg(graphql_client_query_data, uuid, token, device, settings):
    settings.ALLOWED_TRIP_UPDATE_HOURS = 24*365*1000  # hopefully that's enough
    leg = LegFactory(trip__device=device, nr_passengers=1)
    nr_passengers = 2
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!, $leg: ID!, $nrPassengers: Int!)
        @device(uuid: $uuid, token: $token) {
          updateLeg(leg: $leg, nrPassengers: $nrPassengers) {
            ok
            leg {
              id
              nrPassengers
            }
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token, 'leg': leg.id, 'nrPassengers': nr_passengers}
    )
    assert data['updateLeg']['ok'] is True
    assert data['updateLeg']['leg']['id'] == str(leg.id)
    assert data['updateLeg']['leg']['nrPassengers'] == nr_passengers
    leg.refresh_from_db()
    assert leg.nr_passengers == nr_passengers


def test_clear_user_data(graphql_client_query_data, device):
    trip = TripFactory(device=device)
    leg = LegFactory(trip=trip)
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          clearUserData {
            ok
          }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['clearUserData']['ok'] is True
    assert not Device.objects.filter(id=device.id).exists()
    assert not Leg.objects.filter(id=leg.id).exists()
    assert not Trip.objects.filter(id=trip.id).exists()


def test_register_device_sets_account_key(uuid, token, device, register_device):
    assert not device.account_key
    account_key = '12345678-1234-1234-1234-123456789012'
    assert not Device.objects.filter(account_key=account_key).exists()
    register_device(uuid, token, account_key)
    device.refresh_from_db()
    assert device.account_key == account_key
    # Other stuff registering is supposed to do is tested in test_models.py


def test_register_device_already_registered(graphql_client_query, contains_error):
    device1 = DeviceFactory(register_after_creation=True)
    device2 = DeviceFactory(register_after_creation=True)
    response = graphql_client_query(
        '''
        mutation($uuid: String!, $token: String!, $accountKey: String!)
        @device(uuid: $uuid, token: $token)
        {
          registerDevice(accountKey: $accountKey, confirmDeviceMigration: true) {
            ok
          }
        }
        ''',
        variables={'uuid': str(device1.uuid), 'token': str(device1.token), 'accountKey': str(device2.account_key)}
    )
    assert contains_error(response, message="Device already registered")


def test_register_device_migration_not_confirmed(graphql_client_query, contains_error):
    device1 = DeviceFactory(register_after_creation=False)
    device2 = DeviceFactory(register_after_creation=True)
    response = graphql_client_query(
        '''
        mutation($uuid: String!, $token: String!, $accountKey: String!)
        @device(uuid: $uuid, token: $token)
        {
          registerDevice(accountKey: $accountKey) {
            ok
          }
        }
        ''',
        variables={'uuid': str(device1.uuid), 'token': str(device1.token), 'accountKey': str(device2.account_key)}
    )
    assert contains_error(response, code='NEED_CONFIRMATION')


# TODO: unregister

def test_enroll_lottery(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            pollEnrollLottery(name: "testUser", email: "mail@test.com") {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    
    assert data['pollEnrollLottery']['ok'] is True


def test_add_survey(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            pollAddSurvey(days: 3, description: "kokeilu", startDay: "2023-04-15", endDay: "2023-04-17", maxBackQuestion: 3) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollAddSurvey']['ok'] is True

def test_enroll_to_survey(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            pollEnrollToSurvey(surveyId: 2, backQuestionAnswers: "{'x':5, 'y':6}", feelingQuestionAnswers: "{'x':5, 'y':6}") {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollEnrollToSurvey']['ok'] is True

def test_add_user_answer_to_questions(graphql_client_query_data, uuid, token, partisipants):
    partisipants
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            pollAddUserAnswerToQuestions(surveyId: 2, backQuestionAnswers: "{'x':5,'y':6}", feelingQuestionAnswers: "{'x':5, 'y':6}") {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollAddUserAnswerToQuestions']['ok'] is True

def test_add_question(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            pollAddQuestion(description:"test2", question: "{'x':5,'y':6}", questionType: "background", surveyId: 2) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollAddQuestion']['ok'] is True



def test_survey_info_query(graphql_client_query_data, uuid, token):
    survey = SurveyInfoFactory
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          pollSurveyInfo {
              startDay
              endDay
              days
              maxBackQuestion
              description
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'pollSurveyInfo':[
            {
                'startDay': survey.start_day,
                'endDay': survey.end_day,
                'days': survey.days,
                'maxBackQuestion': survey.max_back_question,
                'description': survey.description
            }
        ]
    }
    assert data == expected

def test_user_survey_query(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          pollUserSurvey {
              startDate
              endDate
              approved
              backQuestionAnswers
              feelingQuestionAnswers
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'pollUserSurvey':[]
    }
    assert data == expected

def test_survey_questions_query(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          pollSurveyQuestions(questionType: "background", surveyId: 2) {
              id
              questionData
              questionType
              description
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'pollSurveyQuestions':[]
    }
    assert data == expected

def test_survey_question_query(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          pollSurveyQuestion(questionId: 10) {
              id
              questionData
              questionType
              description
          }
        }
        ''',
        variables={'uuid': uuid, 'token':token}
    )
    expected = {
        'pollSurveyQuestion':[]
    }
    assert data == expected

@freeze_time("2023-07-15")
def test_add_trip(graphql_client_query_data, uuid, token, partisipants,day_info):
    partisipants
    day_info
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollAddTrip(startTime: "2023-07-15T10:59:40", endTime: "2023-07-15T11:59:45", surveyId: 2) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollAddTrip']['ok'] == '1'

@freeze_time("2023-07-15")
def test_add_leg(graphql_client_query_data, uuid, token, survey_trip, day_info, partisipants):
    survey_trip
    day_info
    partisipants
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollAddLeg(tripId: 1, startTime: "2023-07-15T10:59:40", endTime: "2023-07-15T11:59:45", tripLength: 3000, transportMode: "walk")  {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollAddLeg']['ok'] is True

@freeze_time("2023-07-15")
def test_del_leg(graphql_client_query_data, uuid, token, survey_leg):
    survey_leg
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollDelLeg(tripId: 1, legId: 1, surveyId: 2)  {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollDelLeg']['ok'] is True

@freeze_time("2023-07-15")
def test_del_trip(graphql_client_query_data, uuid, token, survey_trip):
    survey_trip
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollDelTrip(tripId: 1, surveyId: 2) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollDelTrip']['ok'] is True

def test_day_trips_query(graphql_client_query_data, uuid, token, survey_trip):
    survey_trip
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          pollDayTrips(day: "2023-07-15", surveyId: 2)  {
              id
              startTime
              endTime
              originalTrip
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'pollDayTrips':[
            {
                'endTime': '2023-07-15T23:59:45+00:00',
                'id': '1',
                'originalTrip': True,
                 'startTime': '2023-07-15T20:59:40+00:00'
            }
        ]
    }
    assert data == expected

def test_trips_legs_query(graphql_client_query_data, uuid, token):
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
          pollTripsLegs(tripId: 1)  {
              id
              startTime
              endTime
              tripLength
              transportMode
              originalLeg
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'pollTripsLegs':[]
    }
    assert data == expected

@freeze_time("2023-07-15")
def test_join_trip(graphql_client_query_data, uuid, token, survey_trip, survey_trip2):
    survey_trip
    survey_trip2
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollJoinTrip(tripId: 1, trip2Id: 2, surveyId: 2)  {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollJoinTrip']['ok'] is True

@freeze_time("2023-07-15")
def test_split_trip(graphql_client_query_data, uuid, token, survey_leg, survey_leg2, day_info, partisipants):
    survey_leg
    survey_leg2
    day_info
    partisipants
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollSplitTrip(tripId: 1, afterLegId: 1, surveyId: 2) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollSplitTrip']['ok'] is True

@freeze_time("2023-07-15")
def test_edit_trip_times(graphql_client_query_data, uuid, token, survey_trip, day_info, partisipants):
    survey_trip
    day_info
    partisipants
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
           pollEditTrip(tripId: 1, startTime: "2023-07-15T10:59:40", endTime: "2023-07-15T11:59:45", surveyId: 2) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollEditTrip']['ok'] is True

@freeze_time("2023-07-15")
def test_mark_user_day_ready(graphql_client_query_data, uuid, token, day_info, partisipants):
    day_info
    partisipants
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            pollMarkUserDayReady(selectedDate: "2023-07-15", surveyId: 2) {
            ok
            }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    assert data['pollMarkUserDayReady']['ok'] is True