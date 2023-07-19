from django.db import models
from enum import Enum
from django.db import transaction
from django.contrib.gis.db import models
from datetime import datetime, timedelta
import random
import logging
import pytz
from django.conf import settings
from django.utils import timezone

LOCAL_TZ = pytz.timezone(settings.TIME_ZONE)
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
        max_length=15,
        default=Question_type_choice('backgroud').value,
        choices=[(tag, tag.value) for tag in Question_type_choice] 
    )
    is_use = models.BooleanField(default=True)
    description = models.TextField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="question_type",
                check=models.Q(question_type__in=Question_type_choice._member_map_),
            )
        ]

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

    def getParpartisipantApprovedVal(self):
        return self.get_partisipant_approved_display()


    class Meta:
        unique_together = ('device', 'survey_info')
        constraints = [
            models.CheckConstraint(
                name="partisipant_approved",
                check=models.Q(partisipant_approved__in=Approved_choice._member_map_),
            )
        ]



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

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="poll_approved",
                check=models.Q(poll_approved__in=Approved_choice._member_map_),
            )
        ]

class Lottery(models.Model):
    user_name = models.TextField()
    user_email = models.EmailField()

class Trips(models.Model):
    partisipant = models.ForeignKey(
        'poll.Partisipants', on_delete=models.CASCADE, null=True
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    original_trip = models.BooleanField(null=True, default=True)
    deleted = models.BooleanField(null=True, default=False)

    def deleteTrip(self):
        if self.original_trip == True:
            self.deleted = True
            self.save()
        else:
            self.delete()

class Legs(models.Model):
    trip = models.ForeignKey(
        'poll.Trips', on_delete=models.CASCADE, null=True
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    trip_length = models.FloatField()

    carbon_footprint = models.FloatField(null=True)

    start_loc = models.PointField(null=True, srid=4326)
    end_loc = models.PointField(null=True, srid=4326)

    nr_passengers = models.IntegerField(null=True)

    transport_mode = models.CharField(
        max_length=20,
         null=True
    )
       

    original_leg = models.BooleanField(null=True,default=True)
    deleted = models.BooleanField(null=True, default=False)

    def deleteLeg(self):
        if self.original_leg == True:
            self.deleted = True
            self.save()
        else:
            self.delete()

        return True

class LegsLocationQuerySet(models.QuerySet):
    def _get_expired_query(self):
        now = timezone.now()
        expiry_time = now - timedelta(hours=settings.ALLOWED_TRIP_UPDATE_HOURS)
        qs = Q(leg__start_time__lte=expiry_time)
        return qs

    def expired(self):
        return self.filter(self._get_expired_query())

    def active(self):
        return self.exclude(self._get_expired_query())


class LegsLocation(models.Model):
    leg = models.ForeignKey(Legs, on_delete=models.CASCADE, related_name='locations')
    loc = models.PointField(null=False, srid=4326)
    time = models.DateTimeField()
    speed = models.FloatField()

    objects = LegsLocationQuerySet.as_manager()

    class Meta:
        ordering = ('leg', 'time')

    def __str__(self):
        time = self.time.astimezone(LOCAL_TZ)
        return '%s: %s (%.1f km/h)' % (time, self.loc, self.speed * 3.6)