# Generated by Django 3.1.9 on 2022-08-10 09:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0028_add_device_groups'),
        ('notifications', '0003_event_type_bronze_or_worse'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationtemplate',
            name='groups',
            field=models.ManyToManyField(blank=True, to='trips.DeviceGroup'),
        ),
        migrations.AddField(
            model_name='notificationtemplate',
            name='send_on',
            field=models.DateField(blank=True, help_text='Date on which the timed notification will be sent', null=True),
        ),
        migrations.AlterField(
            model_name='notificationtemplate',
            name='event_type',
            field=models.CharField(choices=[('monthly_summary_gold', 'Monthly summary (gold-level budget)'), ('monthly_summary_silver', 'Monthly summary (silver-level budget)'), ('monthly_summary_geq_bronze', 'Monthly summary (bronze-level budget or worse)'), ('monthly_summary_bronze', 'Monthly summary (bronze-level budget)'), ('monthly_summary_no_level', 'Monthly summary (worse than bronze budget)'), ('welcome_message', 'Welcome message'), ('no_recent_trips', 'No recent trips'), ('timed_message', 'Timed message')], max_length=26),
        ),
    ]
