
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

        with transaction.atomic():
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

        partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

        dayInfoObj = DayInfo.objects.get(date=selectedDate,partisipants=partisipantObj)
        dayInfoObj.poll_approved = "Yes"

        dayInfoObj.save()

        return dict(ok=True)

class AddTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        start_time = graphene.DateTime(required=True)
        end_time = graphene.DateTime(required=True)
        surveyId = graphene.ID(required=False)

    ok = graphene.ID()

    @classmethod
    def mutate(cls, root, info, start_time,end_time,surveyId):
        device = info.context.device

        partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

        tripObj = Trips()
        tripObj.partisipant = partisipantObj
        tripObj.start_time = start_time
        tripObj.end_time = end_time
        tripObj.original_trip = False

        tripObj.save()

        return dict(ok=tripObj.pk)

class AddLeg(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        start_time = graphene.DateTime(required=True)
        end_time = graphene.DateTime(required=True)
        trip_length = graphene.Float(required=False)
        transport_mode = graphene.String(required=False)
   #     carbon_footprint = graphene.Float(required=False)
   #     transport_mode = graphene.String(required=False)
        #start_loc = graphene.String(required=False)
     #   start_loc = graphene.Field(LegLocationNode)
     #   end_loc = graphene.String(required=False)
   #     end_loc = graphene.Field(LegLocationNode,required=False)
    #    nr_passengers = graphene.Int(required=False)
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, start_time, end_time, trip_length, transport_mode):
    #def mutate(cls, root, info, trip_id, start_time, end_time, trip_length, carbon_footprint, transport_mode, start_loc, end_loc, nr_passengers):
    #def mutate(cls, root, info, trip_id, start_time, end_time, trip_length, carbon_footprint, transport_mode, nr_passengers):
    

        tripObj = Trips.objects.get(pk=trip_id)

        legsObj = Legs()
        legsObj.trip = tripObj
        legsObj.start_time = start_time
        legsObj.end_time = end_time
        legsObj.trip_length = trip_length
   #     legsObj.carbon_footprint = carbon_footprint
        legsObj.transport_mode = transport_mode
        legsObj.original_leg = False
 #       legsObj.start_loc = start_loc
 #       legsObj.end_loc = end_loc
     #   legsObj.nr_passengers = nr_passengers

        legsObj.save()

        return dict(ok=True)

class DelTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, surveyId):
        device = info.context.device

        partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

        tripObj = Trips.objects.get(partisipant=partisipantObj,pk=trip_id)

        tripObj.deleteTrip()

        return dict(ok=True)

class DelLeg(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        leg_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, surveyId, leg_id):
        device = info.context.device

        partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

        tripObj = Trips.objects.get(partisipant=partisipantObj,pk=trip_id)

        legObj = Legs.objects.get(trip=tripObj,pk=leg_id)

        legObj.deleteLeg()

        return dict(ok=True)

class JoinTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        trip2_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, trip2_id, surveyId):
        device = info.context.device

        with transaction.atomic():
            partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

            tripKeepObj = Trips.objects.get(partisipant=partisipantObj,pk=trip_id)
            tripRemoveObj = Trips.objects.get(partisipant=partisipantObj,pk=trip2_id)

            legsObj = Legs.objects.filter(trip=trip2_id)

            legsObj.update(trip = tripKeepObj)

            tripRemoveObj.deleteTrip()


        return dict(ok=True)

class SplitTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        leg_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, leg_id, surveyId):
        device = info.context.device

        with transaction.atomic():
            partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

            lastLeg = Legs.objects.get(pk=leg_id)

            legsObj = Legs.objects.filter(trip=trip_id, start_time__gt=lastLeg.start_time).order_by("start_time")
            first = True
            newStartTime = lastLeg.start_time
            newEndTime = lastLeg.end_time
            

            for legs in legsObj:
                if first == True:
                    first = False
                    newStartTime = legs.start_time
                
                newEndTime = legs.end_time


            tripObj = Trips()
            tripObj.partisipant = partisipantObj
            tripObj.start_time = newStartTime
            tripObj.end_time = newEndTime
            tripObj.original_trip = False

            tripObj.save()

            legsObj.update(trip = tripObj)


        return dict(ok=True)


class Mutations(graphene.ObjectType):
    enrollToSurvey = EnrollToSurvey.Field()
    enrollLottery = EnrollLottery.Field()
    addSurvey = AddSurvey.Field()
    addUserAnswerToQuestions = AddUserAnswerToQuestions.Field()
    addQuestion = AddQuestion.Field()
    markUserDayReady = MarkUserDayReady.Field()
    addTrip = AddTrip.Field()
    addLeg = AddLeg.Field()
    delTrip = DelTrip.Field()
    delLeg = DelLeg.Field()
    joinTrip = JoinTrip.Field()
    splitTrip = SplitTrip.Field()


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

class dayTrips(DjangoObjectType):
    class Meta:
        model = Trips
        field = ("pk", "start_time", "end_time", "original_trip")

class tripsLegs(DjangoObjectType):
    class Meta:
        model = Legs
        field = ("pk", "start_time", "end_time", "original_leg", "trip_length", "transport_mode")

class Query(graphene.ObjectType):
    surveyInfo = graphene.List(Survey)
    userSurvey = graphene.List(UserSurvey)
    surveyQuestions = graphene.List(surveyQuestions, question_type=graphene.String())
    surveyQuestion = graphene.List(surveyQuestion, question_type=graphene.String(), id=graphene.Int())
    dayTrips = graphene.List(dayTrips, day=graphene.Date())
    tripsLegs = graphene.List(tripsLegs, tripId=graphene.Int())

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
    
    def resolve_dayTrips(root, info, day):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        
        partisipantObj = Partisipants.objects.get(device=dev)

        return Trips.objects.filter(partisipant=partisipantObj, start_time__date=day, deleted=False)
    
    def resolve_tripsLegs(root, info, tripId):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        return Legs.objects.filter(deleted=False, trip = tripId)