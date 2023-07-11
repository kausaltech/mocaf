
import graphene


from mocaf.graphql_types import AuthenticatedDeviceNode
from graphene_django import DjangoObjectType
from .models import *
from datetime import date, timedelta
from graphql.error import GraphQLError


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

        for x in range(0, obj.survey_info.days):
            dayInfoObj = DayInfo()
            dayInfoObj.partisipants = obj
            dayInfoObj.date = surveyStartDate
            dayInfoObj.save()
            surveyStartDate = surveyStartDate + timedelta(days=1)

        return dict(ok=True)

class AddUserAnswerToQuestions(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        surveyId = graphene.ID(required=False)
        back_question_answers = graphene.String(required=False)
        feeling_question_answers = graphene.String(required=False)
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, surveyId, back_question_answers, feeling_question_answers):
        device = info.context.device
        obj = Partisipants.objects.get(pk=surveyId,device=device)
        obj.back_question_answers = back_question_answers
        obj.feeling_question_answers = feeling_question_answers

        obj.save()

        return dict(ok=True)

class AddQuestion(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        question = graphene.String(required=True)
        questionType = graphene.String(required=True)
        description = graphene.String(required=True)
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, question, questionType, description):
        obj = Questions()
        obj.question_data = question
        obj.question_type = questionType
        obj.description = description

        obj.save()

        return dict(ok=True)

class MarkUserDayReady(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        selectedDate = graphene.Date(required=True)
        surveyId = graphene.ID(required=False)
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, selectedDate,surveyId):
        device = info.context.device

        PartisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

        dayInfoObj = DayInfo.objects.get(date=selectedDate,partisipants=PartisipantObj)
        dayInfoObj.poll_approved = "Yes"

        dayInfoObj.save()

        return dict(ok=True)

class Mutations(graphene.ObjectType):
    enrollToSurvey = EnrollToSurvey.Field()
    enrollLottery = EnrollLottery.Field()
    addSurvey = AddSurvey.Field()
    addUserAnswerToQuestions = AddUserAnswerToQuestions.Field()
    addQuestion = AddQuestion.Field()
    markUserDayReady = MarkUserDayReady.Field()


class Survey(DjangoObjectType):
    class Meta:
        model = SurveyInfo
        field = ("start_day", "end_day", "days", "max_back_question", "description")

class UserSurvey(DjangoObjectType):
    class Meta:
        model = Partisipants
        field = ("start_date", "end_date", "back_question_answers", "feeling_question_answers")
        exclude = ("partisipant_approved",)

    user_approved = graphene.String()

    def resolve_user_approved(self, info):
        return Partisipants.getParpartisipantApprovedVal(self)

class surveyQuestions(DjangoObjectType):
    class Meta:
        model = Questions
        field = ("pk", "question_data", "question_type", "description")

class surveyQuestion(DjangoObjectType):
    class Meta:
        model = Questions
        field = ("pk", "question_data", "question_type", "description")

class Query(graphene.ObjectType):
    surveyInfo = graphene.List(Survey)
    userSurvey = graphene.List(UserSurvey)
    surveyQuestions = graphene.List(surveyQuestions, question_type=graphene.String())
    surveyQuestion = graphene.List(surveyQuestion, question_type=graphene.String(), id=graphene.Int())

    def resolve_surveyInfo(root, info):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        
        return SurveyInfo.objects.all()
    
    def resolve_userSurvey(root, info):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        return Partisipants.objects.filter(device=dev)
    
    def resolve_surveyQuestions(root, info, question_type):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        
        return Questions.objects.filter(is_use=True, question_type = question_type)
    
    def resolve_surveyQuestion(root, info, question_type, id):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        return Questions.objects.filter(is_use=True, question_type = question_type, pk=id)