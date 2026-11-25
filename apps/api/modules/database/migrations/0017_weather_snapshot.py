from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_climate_prediction"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeatherSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.UUIDField(editable=False, unique=True)),
                ("generated_at", models.DateTimeField()),
                ("provider", models.CharField(max_length=32)),
                ("current_at", models.DateTimeField()),
                ("current_temperature_c", models.FloatField()),
                ("current_relative_humidity_percent", models.FloatField()),
                ("forecast_h1_at", models.DateTimeField()),
                ("forecast_h1_temperature_c", models.FloatField()),
                ("forecast_h1_relative_humidity_percent", models.FloatField()),
            ],
            options={
                "ordering": ["-generated_at", "-pk"],
            },
        ),
    ]
