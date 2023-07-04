
import graphene
import datetime

from mocaf.graphql_types import AuthenticatedDeviceNode
from .models import partisipants
from .models import lottery


class enrollLottery(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
       name = graphene.String(required=True)
       email = graphene.String(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, name, email):
        obj = lottery()

        obj.user_name = name
        obj.user_email = email

        obj.save()

        return dict(ok=True)

class enrollToSurvey(graphene.Mutation, AuthenticatedDeviceNode):
    #class Arguments:
     #   SurveyId = graphene.ID(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info):
        obj = partisipants()

        obj.start_date = datetime.date.today()

        obj.save()

        return dict(ok=True)

        


class Mutations(graphene.ObjectType):
    enrollToSurvey = enrollToSurvey.Field()
    enrollLottery = enrollLottery.Field()
    