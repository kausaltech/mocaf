from django.db import models
from enum import Enum
from django.db import transaction
from django.contrib.gis.db import models
from datetime import datetime, timedelta
import random
import logging


class Approved_choice(Enum):
    No = "No"
    Yes = "Yes"

class Question_type_choice(Enum):
    backgroud = "backgroud"
    feeling = "feeling"
    somethingelse = "somethingelse"

class SurveyInfo(models.Model):
    start_day = models.DateField(null=False)
    end_day = models.DateField(null=False)
    days = models.IntegerField(null=False, default=3)
    max_back_question = models.IntegerField(null=False, default=3)
    description = models.TextField(null=True)

    def get_random_startDate(self):
        delta = timedelta(days=-self.days)
        lastCalcDay = self.end_day + delta
        multiply = (self.end_day - lastCalcDay) * random.random()
        randomDate = self.start_day + multiply
        return randomDate


class Questions(models.Model):
    question_data = models.JSONField(null=True)
    question_type = models.CharField(
        max_length=3,
        default=Question_type_choice('backgroud').value,
        choices=[(tag, tag.value) for tag in Question_type_choice] 
    )
    is_used = models.BooleanField(default=True)

class Partisipants(models.Model):
    device = models.ForeignKey(
        'trips.Device', on_delete=models.CASCADE, null=True
    )
    
    survey_info = models.ForeignKey(
        'poll.SurveyInfo', on_delete=models.CASCADE, null=True
    )

    start_date = models.DateField(null=False)
    end_date = models.DateField(null=True)


    partisipant_approved = models.CharField(
        max_length=3,
        default=Approved_choice('No').value,
        choices=[(tag, tag.value) for tag in Approved_choice] 
    )


#    back_question = models.ForeignKey(
#        'poll.questions', on_delete=models.PROTECT, null=True, limit_choices_to={'question_type': 'backgroud'}, related_name='+'
#    )

    
    back_question_answers = models.JSONField(null=True)


#    feeling_question = models.ForeignKey(
#        'poll.questions', on_delete=models.PROTECT, null=True, limit_choices_to={'question_type': 'feeling'}, related_name='+'
#    )

    feeling_question_answers = models.JSONField(null=True)


class DayInfo(models.Model):
    partisipants = models.ForeignKey(
        'poll.Partisipants', on_delete=models.CASCADE, null=True
    )

    date = models.DateField(null=False)

    poll_approved = models.CharField(
        max_length=3,
        default=Approved_choice('No').value,
        choices=[(tag, tag.value) for tag in Approved_choice] 
    )

class Lottery(models.Model):
    user_name = models.TextField()
    user_email = models.EmailField()

class Trips(models.Model):
    partisipants = models.ForeignKey(
        'poll.Partisipants', on_delete=models.CASCADE, null=True
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

class Legs(models.Model):
    trip_id = models.ForeignKey(
        'poll.Trips', on_delete=models.CASCADE, null=True
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    trip_length = models.FloatField()

    carbon_footprint = models.FloatField(null=True)

    start_loc = models.PointField(null=False, srid=4326)
    end_loc = models.PointField(null=False, srid=4326)

    nr_passengers = models.IntegerField(null=True)

    transport_mode = models.CharField(
        max_length=20,
    )