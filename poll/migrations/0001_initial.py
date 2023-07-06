# Generated by Django 3.1.9 on 2023-07-06 08:48

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import poll.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('trips', '0029_add_health_impact_enabled_to_device'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lottery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.TextField()),
                ('user_email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Partisipants',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True)),
                ('partisipant_approved', models.CharField(choices=[(poll.models.Approved_choice['No'], 'No'), (poll.models.Approved_choice['Yes'], 'Yes')], default='No', max_length=3)),
                ('back_question_answers', models.JSONField(null=True)),
                ('feeling_question_answers', models.JSONField(null=True)),
                ('device', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='trips.device')),
            ],
        ),
        migrations.CreateModel(
            name='Questions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_data', models.JSONField(null=True)),
                ('question_type', models.CharField(choices=[(poll.models.Question_type_choice['backgroud'], 'backgroud'), (poll.models.Question_type_choice['feeling'], 'feeling'), (poll.models.Question_type_choice['somethingelse'], 'somethingelse')], default='backgroud', max_length=3)),
                ('is_used', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_day', models.DateField()),
                ('end_day', models.DateField()),
                ('days', models.IntegerField(default=3)),
                ('max_back_question', models.IntegerField(default=3)),
                ('description', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Trips',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orig_trip_id', models.BigIntegerField()),
                ('orig_leg_id', models.BigIntegerField()),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('trip_length', models.FloatField()),
                ('carbon_footprint', models.FloatField(null=True)),
                ('start_loc', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('end_loc', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('nr_passengers', models.IntegerField(null=True)),
                ('transport_mode', models.CharField(max_length=20)),
                ('partisipants', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='poll.partisipants')),
            ],
        ),
        migrations.AddField(
            model_name='partisipants',
            name='survey_info',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='poll.surveyinfo'),
        ),
        migrations.CreateModel(
            name='DayInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('poll_approved', models.CharField(choices=[(poll.models.Approved_choice['No'], 'No'), (poll.models.Approved_choice['Yes'], 'Yes')], default='No', max_length=3)),
                ('partisipants', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='poll.partisipants')),
            ],
        ),
    ]
