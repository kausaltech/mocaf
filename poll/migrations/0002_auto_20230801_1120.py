# Generated by Django 3.1.9 on 2023-08-01 11:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dayinfo',
            old_name='partisipants',
            new_name='partisipant',
        ),
    ]
