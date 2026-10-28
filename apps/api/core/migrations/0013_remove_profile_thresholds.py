"""Suppression des seuils d'alarme de ThresholdProfile.

Ils ont été convertis en règles d'alarme par 0012_convert_thresholds_to_rules.
Le retour arrière recrée les colonnes avec leurs valeurs par défaut.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_convert_thresholds_to_rules"),
    ]

    operations = [
        migrations.RemoveField(model_name="thresholdprofile", name="co2_critical"),
        migrations.RemoveField(model_name="thresholdprofile", name="co2_warning"),
        migrations.RemoveField(model_name="thresholdprofile", name="humidity_max"),
        migrations.RemoveField(model_name="thresholdprofile", name="humidity_min"),
        migrations.RemoveField(model_name="thresholdprofile", name="sound_critical"),
        migrations.RemoveField(model_name="thresholdprofile", name="sound_warning"),
        migrations.RemoveField(model_name="thresholdprofile", name="temperature_max"),
        migrations.RemoveField(model_name="thresholdprofile", name="temperature_min"),
    ]
