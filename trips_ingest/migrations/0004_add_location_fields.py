# Generated by Django 3.1.7 on 2021-03-29 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips_ingest', '0003_add_new_fields'),
    ]

    operations = [
        migrations.RunSQL("""
            ALTER TABLE "trips_ingest_location" ADD COLUMN "created_at" timestamp with time zone;
            ALTER TABLE "trips_ingest_location" ADD COLUMN "debug" BOOLEAN DEFAULT FALSE;
        """, reverse_sql="""
            ALTER TABLE "trips_ingest_location" DROP COLUMN "debug";
            ALTER TABLE "trips_ingest_location" DROP COLUMN "created_at";
        """),
    ]