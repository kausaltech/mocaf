from django import forms
import graphene
from graphene_django.forms.mutation import DjangoModelFormMutation
from mocaf.graphql_types import DjangoNode
from .models import Location, Leg


class Leg(DjangoNode):
    class Meta:
        model = Leg


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location


class Location(DjangoNode):
    class Meta:
        model = Location


class AddLocationsMutation(graphene.Mutation):
    location = graphene.Field(Location)

    class Meta:
        form_class = LocationForm
