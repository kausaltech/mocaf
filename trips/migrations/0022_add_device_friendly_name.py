# Generated by Django 3.1.8 on 2021-05-18 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0021_add_device_custom_config_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='friendly_name',
            field=models.CharField(max_length=40, null=True),
        ),
    ]