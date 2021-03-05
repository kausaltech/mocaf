from django.contrib.gis.db import models
from multigtfs.models import Route


class VehicleLocation(models.Model):
    route = models.ForeignKey(Route, null=True, on_delete=models.SET_NULL)
    direction_ref = models.CharField(max_length=5, null=True)
    vehicle_ref = models.CharField(max_length=30)
    journey_ref = models.CharField(max_length=30)
    time = models.DateTimeField(primary_key=True)
    loc = models.PointField(null=False, srid=3857)
    bearing = models.FloatField(null=True)

    class Meta:
        ordering = ('time',)
        managed = False

    def __str__(self):
        return '%s (%s) - %s - %s' % (
            self.route, self.direction_ref, self.vehicle_ref, self.time
        )
