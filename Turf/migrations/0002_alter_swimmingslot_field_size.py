# Generated by Django 5.0.6 on 2024-09-26 13:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Turf', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swimmingslot',
            name='field_size',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='Turf.fieldsize'),
        ),
    ]
