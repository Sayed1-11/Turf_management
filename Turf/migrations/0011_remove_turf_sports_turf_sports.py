# Generated by Django 5.0.6 on 2024-09-29 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Turf', '0010_sports_alter_turf_sports'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='turf',
            name='sports',
        ),
        migrations.AddField(
            model_name='turf',
            name='sports',
            field=models.ManyToManyField(blank=True, null=True, to='Turf.sports'),
        ),
    ]
