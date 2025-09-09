import os
import json
import uuid
from app.infrastructure.models import Questionnaire, Question, Choice
from django.db import transaction

# Ruta al JSON de Fase 2
FORM_JSON_PATH = os.path.join(os.path.dirname(__file__), 'forms2.json')

print("Cargando JSON de Fase 2...")
with open(FORM_JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

questions = data.get("questions", [])  # Así viene en tu JSON de Microsoft Forms

# Crea o busca el cuestionario de salida
titulo_cuestionario = data.get("title") or data.get("formsProRTTitle") or "Inspección de Vehículos - Fase 2"
version = data.get("version") or "1.0"
timezone = "America/Bogota"

with transaction.atomic():
    cuestionario, created = Questionnaire.objects.get_or_create(
        title=titulo_cuestionario,
        version=version,
        timezone=timezone,
    )
    # Si quieres limpiar todas las preguntas previas de este cuestionario (opcional, pero recomendado):
    cuestionario.questions.all().delete()
    pregunta_id_map = {}

    # Primer paso: crear preguntas con nuevos UUID
    for pregunta in questions:
        nuevo_id = uuid.uuid4()
        q = Question.objects.create(
            id=nuevo_id,
            questionnaire=cuestionario,
            text=pregunta.get("title") or pregunta.get("formsProRTQuestionTitle") or "",
            type=pregunta.get("type", ""),
            required=pregunta.get("required", False),
            order=int(pregunta.get("order", 0))
        )
        pregunta_id_map[pregunta["id"]] = q

    print(f"Preguntas importadas: {len(pregunta_id_map)}")

    # Segundo paso: crear choices y ramificaciones
    choices_count = 0
    branches_with_problem = 0
    for pregunta in questions:
        if "questionInfo" in pregunta and pregunta["questionInfo"]:
            try:
                info = json.loads(pregunta["questionInfo"])
            except Exception as e:
                print(f"Error cargando questionInfo: {e}")
                continue
            if "Choices" in info and info["Choices"]:
                question_instance = pregunta_id_map.get(pregunta["id"])
                for choice in info["Choices"]:
                    branch_to_id = None
                    branch_to = None
                    if "BranchInfo" in choice and choice["BranchInfo"]:
                        branch_to_id = choice["BranchInfo"].get("TargetQuestionId")
                        if branch_to_id:
                            branch_to = pregunta_id_map.get(branch_to_id)
                            if not branch_to:
                                branches_with_problem += 1
                    Choice.objects.create(
                        question=question_instance,
                        text=choice.get("Description", ""),
                        branch_to=branch_to
                    )
                    choices_count += 1
    print(f"Opciones importadas: {choices_count}")
    if branches_with_problem:
        print(f"Ramificaciones rotas (branch_to no encontradas): {branches_with_problem}")

print("¡Migración de Fase 2 completada! Todas las preguntas y opciones están en la base de datos.")
