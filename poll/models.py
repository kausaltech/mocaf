from django.db import models
from enum import Enum
from django.db import transaction
from django.contrib.gis.db import models

class approved_choice(Enum):
    No = "No"
    Yes = "Yes"

class question_type_choice(Enum):
    backgroud = "backgroud"
    feeling = "feeling"
    somethingelse = "somethingelse"

class settings(models.Model):
    days = models.IntegerField(null=False, default=3)
    max_back_question = models.IntegerField(null=False, default=3)

class questions(models.Model):
    question_data = models.JSONField(null=True)
    question_type = models.CharField(
        max_length=3,
        default=question_type_choice.backgroud,
        choices=[(tag, tag.value) for tag in question_type_choice] 
    )
    is_used = models.BooleanField(default=True)

class partisipants(models.Model):
    device = models.ForeignKey(
        'trips.Device', on_delete=models.CASCADE, null=True
    )
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=True)


    partisipant_approved = models.CharField(
        max_length=3,
        default=approved_choice.No,
        choices=[(tag, tag.value) for tag in approved_choice] 
    )

    back_question = models.ForeignKey(
        'poll.questions', on_delete=models.PROTECT, null=True, limit_choices_to={'question_type': 'backgroud'}, related_name='+'
    )

    back_question_answers = models.JSONField(null=True)

    feeling_question = models.ForeignKey(
        'poll.questions', on_delete=models.PROTECT, null=True, limit_choices_to={'question_type': 'feeling'}, related_name='+'
    )

    feeling_question_answers = models.JSONField(null=True)


class days(models.Model):
    partisipants = models.ForeignKey(
        'poll.partisipants', on_delete=models.CASCADE, null=True
    )

    start_date = models.DateField(null=False)

    poll_approved = models.CharField(
        max_length=3,
        default=approved_choice.No,
        choices=[(tag, tag.value) for tag in approved_choice] 
    )

class lottery(models.Model):
    user_name = models.TextField()
    user_email = models.EmailField()


class trips(models.Model):
    partisipants = models.ForeignKey(
        'poll.partisipants', on_delete=models.CASCADE, null=True
    )

    orig_trip_id = models.BigIntegerField()
    orig_leg_id = models.BigIntegerField()

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