# Generated by Django 3.1.8 on 2021-05-15 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips_ingest', '0010_add_location_manual_atype'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReceiveDebugLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(null=True)),
                ('log', models.BinaryField(max_length=5242880, null=True)),
                ('uuid', models.UUIDField()),
                ('received_at', models.DateTimeField(db_index=True)),
            ],
            options={
                'ordering': ('received_at',),
            },
        ),
    ]