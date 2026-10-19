from django.db import migrations, models


def enable_existing_profiles(apps, schema_editor):
    threshold_profile = apps.get_model("core", "ThresholdProfile")
    threshold_profile.objects.update(enabled=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_thresholdprofile_enabled_alter_zone_zone_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="thresholdprofile",
            name="enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="thresholdprofile",
            name="stuck_after_minutes",
            field=models.PositiveIntegerField(default=15),
        ),
        migrations.RunPython(
            enable_existing_profiles,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
