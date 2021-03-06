# Generated by Django 3.1.6 on 2021-02-03 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DailyEmissionBudget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveIntegerField(verbose_name='Year')),
                ('amount', models.FloatField(help_text='Amount of mobility carbon emissions per resident per day (in grams of CO2e.)', verbose_name='Emission amount')),
            ],
            options={
                'verbose_name': 'Daily emission budget',
                'verbose_name_plural': 'Daily emission budgets',
            },
        ),
    ]
