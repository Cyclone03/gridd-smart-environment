from django.contrib import admin

from modules.database.models import ComfortAssessment


@admin.register(ComfortAssessment)
class ComfortAssessmentAdmin(admin.ModelAdmin):
    list_display = ("zone", "assessed_at", "temperature", "humidity", "level", "score")
    readonly_fields = [field.name for field in ComfortAssessment._meta.fields]
    list_filter = ("zone",)
