# Generated by Django 3.1.9 on 2023-07-06 09:53

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trips',
            name='carbon_footprint',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='end_loc',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='nr_passengers',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='orig_leg_id',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='orig_trip_id',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='start_loc',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='transport_mode',
        ),
        migrations.RemoveField(
            model_name='trips',
            name='trip_length',
        ),
        migrations.CreateModel(
            name='Legs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('trip_length', models.FloatField()),
                ('carbon_footprint', models.FloatField(null=True)),
                ('start_loc', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('end_loc', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('nr_passengers', models.IntegerField(null=True)),
                ('transport_mode', models.CharField(max_length=20)),
                ('trip_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='poll.trips')),
            ],
        ),
    ]
