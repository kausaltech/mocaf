# Generated by Django 3.1.9 on 2022-08-22 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_add_timed_notification_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationtemplate',
            name='event_type',
            field=models.CharField(choices=[('monthly_summary_gold', 'Monthly summary (gold-level budget)'), ('monthly_summary_silver', 'Monthly summary (silver-level budget)'), ('monthly_summary_geq_bronze', 'Monthly summary (bronze-level budget or worse)'), ('monthly_summary_bronze', 'Monthly summary (bronze-level budget)'), ('monthly_summary_no_level', 'Monthly summary (worse than bronze budget)'), ('welcome_message', 'Welcome message'), ('no_recent_trips', 'No recent trips'), ('health_summary_gold', 'Health summary (gold-level budget)'), ('health_summary_silver', 'Health summary (silver-level budget)'), ('health_summary_bronze', 'Health summary (bronze-level budget)'), ('health_summary_no_level', 'Health summary (worse than bronze budget)'), ('health_summary_no_data', 'Health summary (no physical activity trips)'), ('timed_message', 'Timed message')], max_length=26),
        ),
    ]
