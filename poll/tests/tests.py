import pytest
from poll.tests.factories import (ParticipantsFactory, QuestionsFactory, LotteryFactory, LegsFactory, TripsFactory, SurveyInfoFactory)

pytestmark = pytest.mark.django.db

def test_enroll_lottery(graphql_client_query_data, device):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            enrollLottery(name: $user, email: $email) {
            ok
            }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['enrollLottery']['ok'] is True

def test_add_survey(graphql_client_query_data, device):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            addSurvey(days: $days, description: $desc, startDay: $start_date, endDay: $end_date, maxBackQuestion: $max_question) {
            ok
            }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['addSurvey']['ok'] is True

def test_enroll_to_survey(graphql_client_query_data, device):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            enrollToSurvey(surveyId: $id, backQuestionAnswers: $question_answers, feelingQuestionAnswers: $feeling_answers) {
            ok
            }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['enrollToSurvey']['ok'] is True

def test_add_user_answer_to_questions(graphql_client_query_data, device):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            addUserAnswerToQuestions(surveyId: $id, backQuestionAnswers: $question_answers, feelingQuestionAnswers: $feeling_answers) {
            ok
            }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['addUserAnswerToQuestions']['ok'] is True

def test_add_question(graphql_client_query_data, device):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            addQuestion(description: $desc, question: $question, questionType: $type) {
            ok
            }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['addQuestion']['ok'] is True

def test_mark_user_day_ready(graphql_client_query_data, device):
    data = graphql_client_query_data(
        '''
        mutation($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token) {
            markUserDayReady(selectedDate: $date, surveyId: $id) {
            ok
            }
        }
        ''',
        variables={'uuid': str(device.uuid), 'token': str(device.token)}
    )
    assert data['markUserDayReady']['ok'] is True

def test_survey_info_query(graphql_client_query_data, device):
    survey = SurveyInfoFactory
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        surveyInfo {
            startDay
    		    endDay
    		    days
    		    maxBackQuestion
    		    description
        }
        ''',
        variables={'uuid': device.uuid, 'token': device.token}
    )
    expected = {
        'surveyInfo':[
            {
                'startDay': survey.start_day.isoformat(),
                'endDay': survey.end_day.isoformat(),
                'days': survey.days,
                'maxBackQuestion': survey.max_back_question,
                'description': survey.description
            }
        ]
    }
    assert data == expected

def test_user_survey_query(graphql_client_query_data, device):
    survey = ParticipantsFactory
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        userSurvey {
            starDate
    		    endDate
    		    userApprover
    		    backQuestionAnswers
    		    feelingQuestionAnswers
        }
        ''',
        variables={'uuid': device.uuid, 'token': device.token}
    )
    expected = {
        'userSurvey':[
            {
                'startDate': survey.start_date.isoformat(),
                'endDate': survey.end_date.isoformat(),
                'userApproved': survey.participants_approved,
                'backQuestionAnswers': survey.back_question_answers,
                'feelingQuestionAnswer': survey.feeling_question_answers
            }
        ]
    }
    assert data == expected

def test_survery_questions_query(graphql_client_query_data, device):
    survey = ParticipantsFactory
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        surveyQuestions(questionType: "backgroud") {
            id
    		    questionData
    		    questionType
    		    description
        }
        ''',
        variables={'uuid': device.uuid, 'token': device.token}
    )
    expected = {
        'userSurvey':[
            {
                'startDate': survey.start_date.isoformat(),
                'endDate': survey.end_date.isoformat(),
                'userApproved': survey.participants_approved,
                'backQuestionAnswers': survey.back_question_answers,
                'feelingQuestionAnswer': survey.feeling_question_answers
            }
        ]
    }
    assert data == expected