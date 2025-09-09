from django.contrib import admin
from .models import Questionnaire, Question, Choice, Answer, Submission, Actor  # Incluye todos los modelos que te interese administrar

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