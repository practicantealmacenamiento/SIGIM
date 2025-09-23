"""
Funciones de mapeo explícito entre modelos de infraestructura y entidades de dominio.

Este módulo implementa el patrón de mapeo explícito para mantener la separación
entre las capas de dominio e infraestructura, evitando el acoplamiento directo
entre entidades de dominio y modelos Django.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.domain.entities import (
    Submission as SubmissionEntity,
    Answer as AnswerEntity,
    Question as QuestionEntity,
    Choice as ChoiceEntity,
    Questionnaire as QuestionnaireEntity
)
from app.infrastructure.models import (
    Submission as SubmissionModel,
    Answer as AnswerModel,
    Question as QuestionModel,
    Choice as ChoiceModel,
    Questionnaire as QuestionnaireModel
)


# =========================
# Mapeo para Submission
# =========================

def submission_model_to_entity(model: SubmissionModel) -> SubmissionEntity:
    """
    Convierte un modelo Django Submission a una entidad de dominio Submission.
    
    Args:
        model: Instancia del modelo Django SubmissionModel
        
    Returns:
        SubmissionEntity: Entidad de dominio inmutable
        
    Raises:
        ValueError: Si el modelo tiene datos inválidos para la entidad
    """
    # Convertir fecha_creacion a UTC si no tiene timezone
    fecha_creacion = model.fecha_creacion
    if fecha_creacion.tzinfo is None:
        fecha_creacion = fecha_creacion.replace(tzinfo=timezone.utc)
    
    # Convertir fecha_cierre a UTC si existe y no tiene timezone
    fecha_cierre = model.fecha_cierre
    if fecha_cierre is not None and fecha_cierre.tzinfo is None:
        fecha_cierre = fecha_cierre.replace(tzinfo=timezone.utc)
    
    return SubmissionEntity(
        id=model.id,
        questionnaire_id=model.questionnaire_id,
        tipo_fase=model.tipo_fase,
        regulador_id=model.regulador_id,
        placa_vehiculo=model.placa_vehiculo,
        finalizado=model.finalizado,
        fecha_creacion=fecha_creacion,
        fecha_cierre=fecha_cierre,
    )


def submission_entity_to_model(
    entity: SubmissionEntity, 
    model: Optional[SubmissionModel] = None
) -> SubmissionModel:
    """
    Convierte una entidad de dominio Submission a un modelo Django.
    
    Args:
        entity: Entidad de dominio SubmissionEntity
        model: Modelo existente a actualizar (opcional). Si no se proporciona,
               se crea una nueva instancia.
               
    Returns:
        SubmissionModel: Modelo Django actualizado o nuevo
        
    Note:
        Esta función no guarda el modelo en la base de datos.
        El llamador es responsable de llamar .save() si es necesario.
    """
    if model is None:
        model = SubmissionModel()
    
    # Mapear campos directamente
    model.id = entity.id
    model.questionnaire_id = entity.questionnaire_id
    model.tipo_fase = entity.tipo_fase
    model.regulador_id = entity.regulador_id
    model.placa_vehiculo = entity.placa_vehiculo
    model.finalizado = entity.finalizado
    model.fecha_creacion = entity.fecha_creacion
    model.fecha_cierre = entity.fecha_cierre
    
    return model


def update_submission_model_from_entity(
    model: SubmissionModel, 
    entity: SubmissionEntity
) -> SubmissionModel:
    """
    Actualiza un modelo Django existente con datos de una entidad de dominio.
    
    Esta función es útil cuando se quiere actualizar un modelo existente
    sin crear una nueva instancia, preservando relaciones y otros campos
    que no están en la entidad de dominio.
    
    Args:
        model: Modelo Django existente a actualizar
        entity: Entidad de dominio con los nuevos datos
        
    Returns:
        SubmissionModel: El mismo modelo actualizado (para encadenamiento)
    """
    model.questionnaire_id = entity.questionnaire_id
    model.tipo_fase = entity.tipo_fase
    model.regulador_id = entity.regulador_id
    model.placa_vehiculo = entity.placa_vehiculo
    model.finalizado = entity.finalizado
    model.fecha_creacion = entity.fecha_creacion
    model.fecha_cierre = entity.fecha_cierre
    
    return model


# =========================
# Mapeo para Answer
# =========================

def answer_model_to_entity(model: AnswerModel) -> AnswerEntity:
    """
    Convierte un modelo Django Answer a una entidad de dominio Answer.
    
    Args:
        model: Instancia del modelo Django AnswerModel
        
    Returns:
        AnswerEntity: Entidad de dominio inmutable
        
    Raises:
        ValueError: Si el modelo tiene datos inválidos para la entidad
    """
    # Convertir timestamp a UTC si no tiene timezone
    timestamp = model.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    
    # Extraer el path del archivo si existe
    answer_file_path = None
    if model.answer_file:
        answer_file_path = model.answer_file.name
    
    # Obtener choice_id si existe
    answer_choice_id = None
    if model.answer_choice:
        answer_choice_id = model.answer_choice.id
    
    # Obtener user_id si existe
    user_id = None
    if model.user:
        user_id = model.user.id
    
    return AnswerEntity.rehydrate(
        id=model.id,
        submission_id=model.submission_id,
        question_id=model.question_id,
        user_id=user_id,
        answer_text=model.answer_text,
        answer_choice_id=answer_choice_id,
        answer_file_path=answer_file_path,
        ocr_meta=dict(model.ocr_meta or {}),
        meta=dict(model.meta or {}),
        timestamp=timestamp,
    )


def answer_entity_to_model(
    entity: AnswerEntity, 
    model: Optional[AnswerModel] = None
) -> AnswerModel:
    """
    Convierte una entidad de dominio Answer a un modelo Django.
    
    Args:
        entity: Entidad de dominio AnswerEntity
        model: Modelo existente a actualizar (opcional). Si no se proporciona,
               se crea una nueva instancia.
               
    Returns:
        AnswerModel: Modelo Django actualizado o nuevo
        
    Note:
        Esta función no guarda el modelo en la base de datos ni maneja
        las relaciones FK (submission, question, choice, user).
        El llamador es responsable de:
        1. Establecer las relaciones FK apropiadas
        2. Manejar el campo answer_file si es necesario
        3. Llamar .save() si es necesario
    """
    if model is None:
        model = AnswerModel()
    
    # Mapear campos directos
    model.id = entity.id
    model.submission_id = entity.submission_id
    model.question_id = entity.question_id
    model.answer_text = entity.answer_text
    model.ocr_meta = dict(entity.ocr_meta)
    model.meta = dict(entity.meta)
    model.timestamp = entity.timestamp
    
    # Nota: Los campos FK (submission, question, answer_choice, user) 
    # y el campo answer_file deben ser manejados por el llamador
    # ya que requieren acceso a la base de datos para resolver las relaciones
    
    return model


def update_answer_model_from_entity(
    model: AnswerModel, 
    entity: AnswerEntity
) -> AnswerModel:
    """
    Actualiza un modelo Django existente con datos de una entidad de dominio.
    
    Esta función es útil cuando se quiere actualizar un modelo existente
    sin crear una nueva instancia, preservando relaciones y otros campos
    que no están en la entidad de dominio.
    
    Args:
        model: Modelo Django existente a actualizar
        entity: Entidad de dominio con los nuevos datos
        
    Returns:
        AnswerModel: El mismo modelo actualizado (para encadenamiento)
        
    Note:
        Esta función no actualiza las relaciones FK ni el campo answer_file.
        El llamador debe manejar estos campos por separado si es necesario.
    """
    model.submission_id = entity.submission_id
    model.question_id = entity.question_id
    model.answer_text = entity.answer_text
    model.ocr_meta = dict(entity.ocr_meta)
    model.meta = dict(entity.meta)
    model.timestamp = entity.timestamp
    
    return model


def prepare_answer_model_relations(
    model: AnswerModel,
    entity: AnswerEntity
) -> None:
    """
    Prepara las relaciones FK de un modelo Answer basándose en los IDs de la entidad.
    
    Esta función es un helper para establecer las relaciones FK que no pueden
    ser manejadas directamente en las funciones de mapeo principales.
    
    Args:
        model: Modelo Django a actualizar con las relaciones
        entity: Entidad de dominio con los IDs de las relaciones
        
    Note:
        Esta función realiza consultas a la base de datos para resolver las FK.
        Debe ser llamada después de answer_entity_to_model() si se necesitan
        las relaciones establecidas.
    """
    from app.infrastructure.models import Submission, Question, Choice, User
    
    # Establecer relación con submission
    if entity.submission_id:
        try:
            model.submission = Submission.objects.get(id=entity.submission_id)
        except Submission.DoesNotExist:
            model.submission = None
    
    # Establecer relación con question
    if entity.question_id:
        try:
            model.question = Question.objects.get(id=entity.question_id)
        except Question.DoesNotExist:
            model.question = None
    
    # Establecer relación con choice si existe
    if entity.answer_choice_id:
        try:
            model.answer_choice = Choice.objects.get(id=entity.answer_choice_id)
        except Choice.DoesNotExist:
            model.answer_choice = None
    else:
        model.answer_choice = None
    
    # Establecer relación con user si existe
    if entity.user_id:
        try:
            model.user = User.objects.get(id=entity.user_id)
        except User.DoesNotExist:
            model.user = None
    else:
        model.user = None
# =========================
# Mapeo para Choice
# =========================

def choice_model_to_entity(model: ChoiceModel) -> ChoiceEntity:
    """
    Convierte un modelo Django Choice a una entidad de dominio Choice.
    
    Args:
        model: Instancia del modelo Django ChoiceModel
        
    Returns:
        ChoiceEntity: Entidad de dominio inmutable
    """
    # Obtener branch_to_id si existe
    branch_to = None
    if model.branch_to:
        branch_to = model.branch_to.id
    
    return ChoiceEntity(
        id=model.id,
        text=model.text,
        branch_to=branch_to,
    )


def choice_entity_to_model(
    entity: ChoiceEntity, 
    model: Optional[ChoiceModel] = None
) -> ChoiceModel:
    """
    Convierte una entidad de dominio Choice a un modelo Django.
    
    Args:
        entity: Entidad de dominio ChoiceEntity
        model: Modelo existente a actualizar (opcional). Si no se proporciona,
               se crea una nueva instancia.
               
    Returns:
        ChoiceModel: Modelo Django actualizado o nuevo
        
    Note:
        Esta función no guarda el modelo en la base de datos ni maneja
        las relaciones FK (question, branch_to).
        El llamador es responsable de establecer estas relaciones.
    """
    if model is None:
        model = ChoiceModel()
    
    model.id = entity.id
    model.text = entity.text
    
    # Nota: Los campos FK (question, branch_to) deben ser manejados por el llamador
    
    return model


# =========================
# Mapeo para Question
# =========================

def question_model_to_entity(model: QuestionModel) -> QuestionEntity:
    """
    Convierte un modelo Django Question a una entidad de dominio Question.
    
    Args:
        model: Instancia del modelo Django QuestionModel
        
    Returns:
        QuestionEntity: Entidad de dominio inmutable
    """
    # Convertir choices relacionadas
    choices = None
    if model.type == "choice":
        choices = [
            choice_model_to_entity(choice_model) 
            for choice_model in model.choices.all()
        ]
    
    return QuestionEntity(
        id=model.id,
        text=model.text,
        type=model.type,
        required=model.required,
        order=model.order,
        choices=choices,
        semantic_tag=model.semantic_tag if model.semantic_tag != "none" else None,
        file_mode=model.file_mode if model.file_mode else None,
    )


def question_entity_to_model(
    entity: QuestionEntity, 
    model: Optional[QuestionModel] = None
) -> QuestionModel:
    """
    Convierte una entidad de dominio Question a un modelo Django.
    
    Args:
        entity: Entidad de dominio QuestionEntity
        model: Modelo existente a actualizar (opcional). Si no se proporciona,
               se crea una nueva instancia.
               
    Returns:
        QuestionModel: Modelo Django actualizado o nuevo
        
    Note:
        Esta función no guarda el modelo en la base de datos ni maneja
        las relaciones FK (questionnaire) ni las choices relacionadas.
        El llamador es responsable de:
        1. Establecer la relación con questionnaire
        2. Manejar las choices por separado usando create_or_update_question_choices()
        3. Llamar .save() si es necesario
    """
    if model is None:
        model = QuestionModel()
    
    model.id = entity.id
    model.text = entity.text
    model.type = entity.type
    model.required = entity.required
    model.order = entity.order
    model.semantic_tag = entity.semantic_tag or "none"
    model.file_mode = entity.file_mode or ""
    
    return model


def create_or_update_question_choices(
    question_model: QuestionModel,
    question_entity: QuestionEntity
) -> None:
    """
    Crea o actualiza las choices de una pregunta basándose en la entidad de dominio.
    
    Esta función maneja la sincronización completa de choices:
    - Crea nuevas choices que no existen
    - Actualiza choices existentes
    - Elimina choices que ya no están en la entidad
    
    Args:
        question_model: Modelo Django de la pregunta (debe estar guardado)
        question_entity: Entidad de dominio con las choices actualizadas
        
    Note:
        Esta función realiza operaciones de base de datos.
        El question_model debe estar guardado antes de llamar esta función.
    """
    if not question_entity.choices:
        # Si no hay choices en la entidad, eliminar todas las existentes
        question_model.choices.all().delete()
        return
    
    # Obtener choices existentes
    existing_choices = {
        choice.id: choice 
        for choice in question_model.choices.all()
    }
    
    # IDs de choices en la entidad
    entity_choice_ids = {choice.id for choice in question_entity.choices}
    
    # Eliminar choices que ya no están en la entidad
    choices_to_delete = set(existing_choices.keys()) - entity_choice_ids
    if choices_to_delete:
        ChoiceModel.objects.filter(
            id__in=choices_to_delete,
            question=question_model
        ).delete()
    
    # Crear o actualizar choices
    for choice_entity in question_entity.choices:
        if choice_entity.id in existing_choices:
            # Actualizar choice existente
            choice_model = existing_choices[choice_entity.id]
            choice_entity_to_model(choice_entity, choice_model)
            choice_model.question = question_model
            choice_model.save()
        else:
            # Crear nueva choice
            choice_model = choice_entity_to_model(choice_entity)
            choice_model.question = question_model
            choice_model.save()


# =========================
# Mapeo para Questionnaire
# =========================

def questionnaire_model_to_entity(model: QuestionnaireModel) -> QuestionnaireEntity:
    """
    Convierte un modelo Django Questionnaire a una entidad de dominio Questionnaire.
    
    Args:
        model: Instancia del modelo Django QuestionnaireModel
        
    Returns:
        QuestionnaireEntity: Entidad de dominio inmutable
    """
    # Convertir questions relacionadas
    questions = [
        question_model_to_entity(question_model)
        for question_model in model.questions.all().order_by('order')
    ]
    
    return QuestionnaireEntity(
        id=model.id,
        title=model.title,
        version=model.version,
        timezone=model.timezone,
        questions=questions,
    )


def questionnaire_entity_to_model(
    entity: QuestionnaireEntity, 
    model: Optional[QuestionnaireModel] = None
) -> QuestionnaireModel:
    """
    Convierte una entidad de dominio Questionnaire a un modelo Django.
    
    Args:
        entity: Entidad de dominio QuestionnaireEntity
        model: Modelo existente a actualizar (opcional). Si no se proporciona,
               se crea una nueva instancia.
               
    Returns:
        QuestionnaireModel: Modelo Django actualizado o nuevo
        
    Note:
        Esta función no guarda el modelo en la base de datos ni maneja
        las questions relacionadas.
        El llamador es responsable de:
        1. Manejar las questions por separado usando create_or_update_questionnaire_questions()
        2. Llamar .save() si es necesario
    """
    if model is None:
        model = QuestionnaireModel()
    
    model.id = entity.id
    model.title = entity.title
    model.version = entity.version
    model.timezone = entity.timezone
    
    return model


def create_or_update_questionnaire_questions(
    questionnaire_model: QuestionnaireModel,
    questionnaire_entity: QuestionnaireEntity
) -> None:
    """
    Crea o actualiza las questions de un cuestionario basándose en la entidad de dominio.
    
    Esta función maneja la sincronización completa de questions y sus choices:
    - Crea nuevas questions que no existen
    - Actualiza questions existentes
    - Elimina questions que ya no están en la entidad
    - Maneja las choices de cada question
    
    Args:
        questionnaire_model: Modelo Django del cuestionario (debe estar guardado)
        questionnaire_entity: Entidad de dominio con las questions actualizadas
        
    Note:
        Esta función realiza operaciones de base de datos.
        El questionnaire_model debe estar guardado antes de llamar esta función.
    """
    # Obtener questions existentes
    existing_questions = {
        question.id: question 
        for question in questionnaire_model.questions.all()
    }
    
    # IDs de questions en la entidad
    entity_question_ids = {question.id for question in questionnaire_entity.questions}
    
    # Eliminar questions que ya no están en la entidad
    questions_to_delete = set(existing_questions.keys()) - entity_question_ids
    if questions_to_delete:
        QuestionModel.objects.filter(
            id__in=questions_to_delete,
            questionnaire=questionnaire_model
        ).delete()
    
    # Crear o actualizar questions
    for question_entity in questionnaire_entity.questions:
        if question_entity.id in existing_questions:
            # Actualizar question existente
            question_model = existing_questions[question_entity.id]
            question_entity_to_model(question_entity, question_model)
            question_model.questionnaire = questionnaire_model
            question_model.save()
        else:
            # Crear nueva question
            question_model = question_entity_to_model(question_entity)
            question_model.questionnaire = questionnaire_model
            question_model.save()
        
        # Manejar choices de la question
        create_or_update_question_choices(question_model, question_entity)