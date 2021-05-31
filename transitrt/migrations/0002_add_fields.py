from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transitrt', '0001_initial'),
        ('trips', '0013_add_mode_variants_and_i18n'),
    ]

    operations = [
        migrations.RunSQL("""
            ALTER TABLE "transitrt_vehiclelocation" ADD COLUMN "loc_error" double precision NULL;
            ALTER TABLE "transitrt_vehiclelocation" ADD COLUMN "speed" double precision NULL;
            ALTER TABLE "transitrt_vehiclelocation" ADD COLUMN "route_type" integer NULL;
        """, reverse_sql="""
            ALTER TABLE "transitrt_vehiclelocation" DROP COLUMN "speed";
            ALTER TABLE "transitrt_vehiclelocation" DROP COLUMN "loc_error";
            ALTER TABLE "transitrt_vehiclelocation" DROP COLUMN "route_type";
        """),
    ]
