from django.contrib import admin

from modules.database.models import ComfortProfile


@admin.register(ComfortProfile)
class ComfortProfileAdmin(admin.ModelAdmin):
    list_display = ("zone", "temperature_min", "temperature_max", "humidity_min", "humidity_max", "updated_at")
