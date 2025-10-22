from django.contrib import admin
from .models import Questionnaire, Question, Choice, Answer, Submission, Actor  # Incluye todos los modelos que te interese administrar
from app.infrastructure.usage_limits import VisionMonthlyUsage

class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "type", "file_mode", "questionnaire", "order", "required")
    list_filter  = ("type", "file_mode", "questionnaire")
    search_fields = ("text",)

admin.site.register(Questionnaire)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(Answer)
admin.site.register(Submission)
admin.site.register(Actor)

@admin.register(VisionMonthlyUsage)
class VisionMonthlyUsageAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "count", "updated_at")
    list_filter = ("year", "month")
    ordering = ("-year", "-month")
    search_fields = ("year", "month")