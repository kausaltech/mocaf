
import graphene


from mocaf.graphql_types import AuthenticatedDeviceNode
from .models import *
from datetime import date, timedelta


class AddSurvey(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        start_day = graphene.Date(required=True)
        end_day = graphene.Date(required=True)
        days = graphene.Int(required=True)
        max_back_question = graphene.Int(required=False)
        description = graphene.String(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, start_day, end_day, days, max_back_question, description):
        obj = SurveyInfo()

        obj.days = days
        obj.start_day = start_day
        obj.end_day = end_day
        obj.max_back_question = max_back_question
        obj.description = description

        obj.save()

        return dict(ok=True)


class EnrollLottery(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
       name = graphene.String(required=True)
       email = graphene.String(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, name, email):
        obj = Lottery()

        obj.user_name = name
        obj.user_email = email

        obj.save()

        return dict(ok=True)

class EnrollToSurvey(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        surveyId = graphene.ID(required=False)
        back_question_answers = graphene.String(required=False)
        feeling_question_answers = graphene.String(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, surveyId, back_question_answers, feeling_question_answers):
        obj = Partisipants()
        obj.device = info.context.device
        obj.survey_info = SurveyInfo.objects.get(pk=surveyId)
        obj.back_question_answers = back_question_answers
        obj.feeling_question_answers = feeling_question_answers

        obj.start_date = date.today()

        obj.save()

        surveyStartDate = obj.survey_info.get_random_startDate()

        for x in range(0, obj.survey_info.max_back_question):
            dayInfoObj = DayInfo()
            dayInfoObj.partisipants = obj
            dayInfoObj.date = surveyStartDate
            dayInfoObj.save()
            surveyStartDate = surveyStartDate + timedelta(days=1)

        return dict(ok=True)

        


class Mutations(graphene.ObjectType):
    enrollToSurvey = EnrollToSurvey.Field()
    enrollLottery = EnrollLottery.Field()
    addSurvey = AddSurvey.Field()
    