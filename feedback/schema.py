import graphene

from mocaf.graphql_types import AuthenticatedDeviceNode
from trips.models import Leg
from .models import DeviceFeedback


class SendFeedbackMutation(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        trip = graphene.ID(required=False)
        leg = graphene.ID(required=False)
        name = graphene.String(required=False)
        comment = graphene.String(required=True)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, comment, trip=None, leg=None, name=None):
        dev = info.context.device
        obj = DeviceFeedback(device=dev)
        if trip:
            obj.trip = dev.trips.filter(id=trip).first()
        if leg:
            obj.leg = Leg.objects.filter(trip__device=dev, id=leg).first()
        obj.name = name
        obj.comment = comment
        obj.save()

        return dict(ok=True)


class Mutations(graphene.ObjectType):
    send_feedback = SendFeedbackMutation.Field()
