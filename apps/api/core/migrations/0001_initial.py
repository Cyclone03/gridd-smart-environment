from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Zone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("zone_type", models.CharField(choices=[("server_room","Salle serveur"),("classroom","Salle de cours"),("office","Bureau"),("lab","Laboratoire"),("other","Autre")], default="other", max_length=30)),
                ("description", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="ThresholdProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("temperature_min", models.FloatField(default=20)),
                ("temperature_max", models.FloatField(default=25)),
                ("humidity_min", models.FloatField(default=30)),
                ("humidity_max", models.FloatField(default=60)),
                ("co2_warning", models.FloatField(default=800)),
                ("co2_critical", models.FloatField(default=1200)),
                ("sound_warning", models.FloatField(default=55)),
                ("sound_critical", models.FloatField(default=70)),
                ("max_temperature_delta_per_minute", models.FloatField(default=5)),
                ("max_humidity_delta_per_minute", models.FloatField(default=20)),
                ("max_co2_delta_per_minute", models.FloatField(default=800)),
                ("max_sound_delta_per_minute", models.FloatField(default=40)),
                ("zone", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="threshold_profile", to="core.zone")),
            ],
        ),
        migrations.CreateModel(
            name="Sensor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_id", models.CharField(max_length=150, unique=True)),
                ("label", models.CharField(blank=True, max_length=150)),
                ("sensor_type", models.CharField(choices=[("temperature","Température"),("humidity","Humidité"),("co2","CO₂"),("sound_level","Niveau sonore"),("occupancy","Occupation")], max_length=30)),
                ("unit", models.CharField(max_length=20)),
                ("active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("zone", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sensors", to="core.zone")),
            ],
        ),
        migrations.CreateModel(
            name="Observation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(max_length=30)),
                ("value", models.FloatField()),
                ("unit", models.CharField(max_length=20)),
                ("observed_at", models.DateTimeField(blank=True, null=True)),
                ("received_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("quality_status", models.CharField(choices=[("normal","Normal"),("suspicious","Suspecte"),("invalid","Invalide")], default="normal", max_length=20)),
                ("quality_reason", models.CharField(blank=True, max_length=255)),
                ("sensor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observations", to="core.sensor")),
                ("zone", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observations", to="core.zone")),
            ],
            options={"ordering": ["-observed_at", "-received_at"]},
        ),
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=80)),
                ("message", models.CharField(max_length=255)),
                ("severity", models.CharField(choices=[("info","Info"),("warning","Attention"),("critical","Critique")], max_length=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("observation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="core.observation")),
                ("zone", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alerts", to="core.zone")),
            ],
        ),
        migrations.AddIndex(
            model_name="observation",
            index=models.Index(fields=["zone", "type", "-observed_at"], name="core_observ_zone_id_90bff1_idx"),
        ),
        migrations.AddIndex(
            model_name="observation",
            index=models.Index(fields=["sensor", "-observed_at"], name="core_observ_sensor__33fc83_idx"),
        ),
    ]
