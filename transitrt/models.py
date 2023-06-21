from django.conf import settings
from django.contrib.gis.db import models
from gtfs.models import Route, FeedInfo


class VehicleLocation(models.Model):
    direction_ref = models.CharField(max_length=5, null=True)
    vehicle_ref = models.CharField(max_length=30)
    journey_ref = models.CharField(max_length=30)
    vehicle_journey_ref = models.CharField(max_length=50)
    time = models.DateTimeField(primary_key=True)
    loc = models.PointField(null=False, srid=settings.LOCAL_SRS)
    loc_error = models.FloatField(null=True)
    bearing = models.FloatField(null=True)
    speed = models.FloatField(null=True)
    route_type = models.PositiveBigIntegerField(null=True)  # matches gtfs route type

    gtfs_route = models.ForeignKey(Route, null=True, on_delete=models.SET_NULL)
    gtfs_feed = models.ForeignKey(FeedInfo, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ('time',)
        managed = False

    def __str__(self):
        return '%s (%s) - %s - %s' % (
            self.route, self.direction_ref, self.vehicle_ref, self.time
        )
