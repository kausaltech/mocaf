# Generated by Django 3.1.8 on 2021-05-02 11:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0014_add_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='leg',
            name='deleted',
        ),
        migrations.AddField(
            model_name='leg',
            name='deleted_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='trip',
            name='deleted_at',
            field=models.DateTimeField(null=True),
        ),
    ]