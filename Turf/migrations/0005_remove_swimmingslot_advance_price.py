# Generated by Django 5.0.6 on 2024-09-28 06:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Turf', '0004_alter_swimmingslot_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='swimmingslot',
            name='advance_price',
        ),
    ]
