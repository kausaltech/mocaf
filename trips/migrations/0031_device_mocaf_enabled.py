# Generated by Django 3.1.9 on 2023-07-24 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0030_device_survey_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='mocaf_enabled',
            field=models.BooleanField(null=True, verbose_name=True),
        ),
    ]
