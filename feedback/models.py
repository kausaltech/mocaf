from django.db import models
from trips.models import Device, Trip, Leg


class DeviceFeedback(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='feedbacks')
    trip = models.ForeignKey(Trip, null=True, on_delete=models.SET_NULL, related_name='feedbacks')
    leg = models.ForeignKey(Leg, null=True, on_delete=models.SET_NULL, related_name='feedbacks')
    name = models.CharField(max_length=100, null=True, blank=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
