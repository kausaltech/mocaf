# Generated by Django 3.1.8 on 2021-05-14 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0018_add_default_device_mode_variant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='model',
            field=models.CharField(max_length=40, null=True),
        ),
    ]
