
import graphene
import pytz


from mocaf.graphql_types import AuthenticatedDeviceNode
from graphene_django import DjangoObjectType
from .models import *
from datetime import date, timedelta
from graphql.error import GraphQLError
from mocaf.graphql_types import AuthenticatedDeviceNode, DjangoNode
from mocaf.graphql_gis import LineStringScalar, PointScalar
from django.db import transaction, DatabaseError

LOCAL_TZ = pytz.timezone('Europe/Helsinki')

class PointModelType(graphene.ObjectType):
    location = graphene.Field(graphene.String, to=PointScalar())


class AddSurvey(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        start_day = graphene.Date(required=True)
        end_day = graphene.Date(required=True)
        days = graphene.Int(required=True)
        max_back_question = graphene.Int(required=False, default_value = "")
        description = graphene.String(required=False, default_value = "")

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, start_day, end_day, days, max_back_question = "", description = ""):
        
        if start_day > (end_day - timedelta(days=days)):
            raise GraphQLError('Times are bad', [info])
        
        obj = SurveyInfo()

        obj.days = days
        obj.start_day = start_day
        obj.end_day = end_day

        if max_back_question != "":
            obj.max_back_question = max_back_question
        
        if description != "":
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
        back_question_answers = graphene.String(required=False, default_value = "")
        feeling_question_answers = graphene.String(required=False, default_value = "")

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, surveyId, back_question_answers = "", feeling_question_answers = ""):
        okVal = True

        try:
            with transaction.atomic():
                obj = Partisipants()
                obj.device = info.context.device
                obj.survey_info = SurveyInfo.objects.get(pk=surveyId)

                if back_question_answers != "":
                    obj.back_question_answers = back_question_answers
                
                if feeling_question_answers != "":
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
        except DatabaseError:
            okVal = False

        return dict(ok=okVal)

class AddUserAnswerToQuestions(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        surveyId = graphene.ID(required=True)
        back_question_answers = graphene.String(required=False, default_value = "")
        feeling_question_answers = graphene.String(required=False, default_value = "")
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, surveyId, back_question_answers = "", feeling_question_answers = ""):
        device = info.context.device
        obj = Partisipants.objects.get(pk=surveyId,device=device)

        if back_question_answers != "":
            obj.back_question_answers = back_question_answers
        
        if feeling_question_answers != "":
            obj.feeling_question_answers = feeling_question_answers

        obj.save()

        return dict(ok=True)

class AddQuestion(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        question = graphene.String(required=True)
        questionType = graphene.String(required=True)
        description = graphene.String(required=True)
        surveyId = graphene.ID(required=False, default_value = "")
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, question, questionType, description, surveyId = ""):
        obj = Questions()
        obj.question_data = question
        obj.question_type = questionType
        obj.description = description

        if surveyId != "":
            surveyInfoObj = SurveyInfo.objects.get(pk=surveyId)
            obj.survey_info = surveyInfoObj

        obj.save()

        return dict(ok=True)

class MarkUserDayReady(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        selectedDate = graphene.Date(required=True)
        surveyId = graphene.ID(required=True)
    
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
        surveyId = graphene.ID(required=True)

    ok = graphene.ID()

    @classmethod
    def mutate(cls, root, info, start_time,end_time,surveyId):
        device = info.context.device

        if start_time >= end_time:
            raise GraphQLError('Times are bad', [info])

        start_time_d = LOCAL_TZ.localize(start_time, is_dst=None)
        end_time_d = LOCAL_TZ.localize(end_time, is_dst=None)

        fixStartTime = start_time_d.astimezone(pytz.utc)
        fixEndTime = end_time_d.astimezone(pytz.utc)

        partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

        tripObj = Trips()
        tripObj.partisipant = partisipantObj
        tripObj.start_time = fixStartTime
        tripObj.end_time = fixEndTime
        tripObj.original_trip = False

        tripObj.save()

        return dict(ok=tripObj.pk)

class AddLeg(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        start_time = graphene.DateTime(required=True)
        end_time = graphene.DateTime(required=True)
        trip_length = graphene.Float(required=False, default_value = "")
        transport_mode = graphene.String(required=False, default_value = "")
        carbon_footprint = graphene.String(required=False, default_value = "")
        nr_passengers = graphene.String(required=False, default_value = "")
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, start_time, end_time, trip_length = "", transport_mode = "", carbon_footprint = "", nr_passengers = ""):

        if start_time >= end_time:
            raise GraphQLError('Times are bad', [info])

        okVal = True

        try:
            with transaction.atomic():
                tripObj = Trips.objects.get(pk=trip_id)
                legsObj = Legs()

                start_time_d = LOCAL_TZ.localize(start_time, is_dst=None)
                end_time_d = LOCAL_TZ.localize(end_time, is_dst=None)
                #fixStartTime = start_time.replace(tzinfo=pytz.UTC)
                fixStartTime = start_time_d.astimezone(pytz.utc)
                #fixStartTime = start_time.replace(tzinfo=LOCAL_TZ)
            #    fixStartTime = start_time.astimezone(LOCAL_TZ).isoformat()
                fixEndTime = end_time_d.astimezone(pytz.utc)
                #fixEndTime = end_time.replace(tzinfo=LOCAL_TZ)
                #fixEndTime = end_time.replace(tzinfo=pytz.UTC)
                #fixEndTime = end_time.astimezone(LOCAL_TZ).isoformat()

                legsObj.trip = tripObj
                legsObj.start_time = fixStartTime
                legsObj.end_time = fixEndTime

                if trip_length != "":
                    legsObj.trip_length = trip_length
                
                if transport_mode != "":
                    legsObj.transport_mode = transport_mode

                if carbon_footprint != "":
                    legsObj.carbon_footprint = carbon_footprint
                
                if nr_passengers != "":
                    legsObj.nr_passengers = nr_passengers
                
                legsObj.original_leg = False

                legsObj.save()

                tripObjChange = False


                if fixStartTime < tripObj.start_time:
                    tripObj.start_time = fixStartTime
                    tripObjChange = True

                if fixEndTime > tripObj.end_time:
                    tripObj.end_time = fixEndTime
                    tripObjChange = True

                if tripObjChange:
                    tripObj.save()

        except DatabaseError:
            okVal = False

        return dict(ok=okVal)

class LocationToLeg(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        loc = location=graphene.Argument(PointScalar)
        leg_id = graphene.ID(required=True)
        time = graphene.DateTime(required=False, default_value = "")
    
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, leg_id, loc,time = ""):

        legsObj = Legs.objects.get(pk=leg_id)

        if legsObj.start_time > time or time > legsObj.end_time:
            raise GraphQLError('Times are bad', [info])

        LogObj = LegsLocation()
        LogObj.leg = legsObj
        LogObj.loc = PointModelType(loc)

        if time != "":
            LogObj.time = time

        LogObj.save()

        return dict(ok=True)

class DelTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=True)

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
        surveyId = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, surveyId, leg_id):
        device = info.context.device
        okVal = True
        
        try:
            with transaction.atomic():
                partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

                tripObj = Trips.objects.get(partisipant=partisipantObj,pk=trip_id)

                legObj = Legs.objects.get(trip=tripObj,pk=leg_id)

                tripObjChange = False

                if tripObj.start_time == legObj.start_time:
                    tripObj.start_time = legObj.end_time
                    tripObjChange = True
                
                if tripObj.end_time == legObj.end_time:
                    tripObj.end_time = legObj.start_time
                    tripObjChange = True
                
                if tripObjChange:
                    tripObj.save()

                legObj.deleteLeg()

        except DatabaseError:
            okVal = False

        return dict(ok=okVal)

class JoinTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        trip2_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, trip2_id, surveyId):
        device = info.context.device

        okVal = True

        try:
            with transaction.atomic():
                partisipantObj = Partisipants.objects.get(pk=surveyId,device=device)

                tripKeepObj = Trips.objects.get(partisipant=partisipantObj,pk=trip_id)
                tripRemoveObj = Trips.objects.get(partisipant=partisipantObj,pk=trip2_id)

                tripObjChange = False

                if tripKeepObj.start_time > tripRemoveObj.start_time:
                    tripKeepObj.start_time = tripRemoveObj.start_time
                    tripObjChange = True

                if tripKeepObj.end_time < tripRemoveObj.end_time:
                    tripKeepObj.end_time = tripRemoveObj.end_time
                    tripObjChange = True
                
                if tripObjChange:
                    tripKeepObj.save()

                legsObj = Legs.objects.filter(trip=trip2_id)

                legsObj.update(trip = tripKeepObj)

                tripRemoveObj.deleteTrip()

        except DatabaseError:
            okVal = False

        return dict(ok=okVal)

class SplitTrip(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip_id = graphene.ID(required=True)
        leg_id = graphene.ID(required=True)
        surveyId = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, trip_id, leg_id, surveyId):
        device = info.context.device
        okVal = True

        try:
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

                oldTripObj = Trips.objects.get(partisipant=partisipantObj,pk=trip_id)

                oldTripObj.end_time = lastLeg.end_time
                oldTripObj.save()

        except DatabaseError:
            okVal = False

        return dict(ok=okVal)


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
    locationToLeg = LocationToLeg.Field()


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
        field = ("pk", "question_data", "question_type", "description", "survey_info")

class surveyQuestion(DjangoObjectType):
    class Meta:
        model = Questions
        field = ("pk", "question_data", "question_type", "description", "survey_info")

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
    surveyQuestions = graphene.List(surveyQuestions, question_type=graphene.String(), survey_id=graphene.Int())
    surveyQuestion = graphene.List(surveyQuestion, question_id=graphene.Int())
    dayTrips = graphene.List(dayTrips, day=graphene.Date(), survey_id=graphene.Int())
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
    
    def resolve_surveyQuestions(root, info, question_type, survey_id = ""):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        
        if survey_id != "":
            return Questions.objects.filter(is_use=True, question_type = question_type, survey_info = survey_id)
        else:
            return Questions.objects.filter(is_use=True, question_type = question_type)
    
    def resolve_surveyQuestion(root, info, question_id):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        return Questions.objects.filter(is_use=True, pk=question_id)
    
    def resolve_dayTrips(root, info, day, survey_id = ""):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        
        if survey_id != "":
            partisipantObj = Partisipants.objects.get(pk=survey_id,device=dev)
        else:   
            partisipantObj = Partisipants.objects.filter(device=dev)[:1]

        return Trips.objects.filter(partisipant=partisipantObj, start_time__date=day, deleted=False)
    
    def resolve_tripsLegs(root, info, tripId):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        return Legs.objects.filter(deleted=False, trip = tripId)