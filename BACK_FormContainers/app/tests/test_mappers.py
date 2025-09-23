"""
Tests para las funciones de mapeo entre modelos y entidades.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

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
from app.infrastructure.mappers import (
    submission_model_to_entity,
    submission_entity_to_model,
    answer_model_to_entity,
    answer_entity_to_model,
    choice_model_to_entity,
    choice_entity_to_model,
    question_model_to_entity,
    question_entity_to_model,
    questionnaire_model_to_entity,
    questionnaire_entity_to_model
)


class TestSubmissionMapping:
    """Tests para mapeo de Submission."""
    
    def test_submission_model_to_entity(self):
        """Test conversión de modelo a entidad."""
        # Crear modelo mock
        model = SubmissionModel()
        model.id = uuid4()
        model.questionnaire_id = uuid4()
        model.tipo_fase = "entrada"
        model.regulador_id = uuid4()
        model.placa_vehiculo = "ABC123"
        model.finalizado = False
        model.fecha_creacion = datetime.now(timezone.utc)
        model.fecha_cierre = None
        
        # Convertir a entidad
        entity = submission_model_to_entity(model)
        
        # Verificar mapeo
        assert entity.id == model.id
        assert entity.questionnaire_id == model.questionnaire_id
        assert entity.tipo_fase == model.tipo_fase
        assert entity.regulador_id == model.regulador_id
        assert entity.placa_vehiculo == model.placa_vehiculo
        assert entity.finalizado == model.finalizado
        assert entity.fecha_creacion == model.fecha_creacion
        assert entity.fecha_cierre == model.fecha_cierre
    
    def test_submission_entity_to_model(self):
        """Test conversión de entidad a modelo."""
        # Crear entidad
        entity = SubmissionEntity.create_new(
            questionnaire_id=uuid4(),
            tipo_fase="salida",
            regulador_id=uuid4(),
            placa_vehiculo="XYZ789"
        )
        
        # Convertir a modelo
        model = submission_entity_to_model(entity)
        
        # Verificar mapeo
        assert model.id == entity.id
        assert model.questionnaire_id == entity.questionnaire_id
        assert model.tipo_fase == entity.tipo_fase
        assert model.regulador_id == entity.regulador_id
        assert model.placa_vehiculo == entity.placa_vehiculo
        assert model.finalizado == entity.finalizado
        assert model.fecha_creacion == entity.fecha_creacion
        assert model.fecha_cierre == entity.fecha_cierre


class TestAnswerMapping:
    """Tests para mapeo de Answer."""
    
    def test_answer_model_to_entity_text_answer(self):
        """Test conversión de modelo a entidad para respuesta de texto."""
        # Crear modelo mock
        model = AnswerModel()
        model.id = uuid4()
        model.submission_id = uuid4()
        model.question_id = uuid4()
        model.user = None
        model.answer_text = "Respuesta de prueba"
        model.answer_choice = None
        model.answer_file = None
        model.ocr_meta = {"confidence": 0.95}
        model.meta = {"source": "manual"}
        model.timestamp = datetime.now(timezone.utc)
        
        # Convertir a entidad
        entity = answer_model_to_entity(model)
        
        # Verificar mapeo
        assert entity.id == model.id
        assert entity.submission_id == model.submission_id
        assert entity.question_id == model.question_id
        assert entity.user_id is None
        assert entity.answer_text == model.answer_text
        assert entity.answer_choice_id is None
        assert entity.answer_file_path is None
        assert entity.ocr_meta == model.ocr_meta
        assert entity.meta == model.meta
        assert entity.timestamp == model.timestamp
    
    def test_answer_entity_to_model(self):
        """Test conversión de entidad a modelo."""
        # Crear entidad
        entity = AnswerEntity.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="Texto de respuesta",
            ocr_meta={"confidence": 0.9},
            meta={"validated": True}
        )
        
        # Convertir a modelo
        model = answer_entity_to_model(entity)
        
        # Verificar mapeo
        assert model.id == entity.id
        assert model.submission_id == entity.submission_id
        assert model.question_id == entity.question_id
        assert model.answer_text == entity.answer_text
        assert model.ocr_meta == entity.ocr_meta
        assert model.meta == entity.meta
        assert model.timestamp == entity.timestamp


class TestChoiceMapping:
    """Tests para mapeo de Choice."""
    
    def test_choice_model_to_entity(self):
        """Test conversión de modelo a entidad."""
        # Crear modelo mock
        model = ChoiceModel()
        model.id = uuid4()
        model.text = "Opción A"
        model.branch_to = None
        
        # Convertir a entidad
        entity = choice_model_to_entity(model)
        
        # Verificar mapeo
        assert entity.id == model.id
        assert entity.text == model.text
        assert entity.branch_to is None
    
    def test_choice_entity_to_model(self):
        """Test conversión de entidad a modelo."""
        # Crear entidad
        entity = ChoiceEntity(
            id=uuid4(),
            text="Opción B",
            branch_to=uuid4()
        )
        
        # Convertir a modelo
        model = choice_entity_to_model(entity)
        
        # Verificar mapeo
        assert model.id == entity.id
        assert model.text == entity.text


class TestQuestionMapping:
    """Tests para mapeo de Question."""
    
    def test_question_model_to_entity_text_question(self):
        """Test conversión de modelo a entidad para pregunta de texto."""
        # Crear modelo mock
        model = QuestionModel()
        model.id = uuid4()
        model.text = "¿Cuál es su nombre?"
        model.type = "text"
        model.required = True
        model.order = 1
        model.semantic_tag = "none"
        model.file_mode = ""
        
        # Mock para choices.all()
        model.choices = type('MockManager', (), {
            'all': lambda: []
        })()
        
        # Convertir a entidad
        entity = question_model_to_entity(model)
        
        # Verificar mapeo
        assert entity.id == model.id
        assert entity.text == model.text
        assert entity.type == model.type
        assert entity.required == model.required
        assert entity.order == model.order
        assert entity.choices is None
        assert entity.semantic_tag is None
        assert entity.file_mode is None
    
    def test_question_entity_to_model(self):
        """Test conversión de entidad a modelo."""
        # Crear entidad
        entity = QuestionEntity(
            id=uuid4(),
            text="¿Cuál es la placa del vehículo?",
            type="text",
            required=True,
            order=2,
            semantic_tag="placa",
            file_mode="image_ocr"
        )
        
        # Convertir a modelo
        model = question_entity_to_model(entity)
        
        # Verificar mapeo
        assert model.id == entity.id
        assert model.text == entity.text
        assert model.type == entity.type
        assert model.required == entity.required
        assert model.order == entity.order
        assert model.semantic_tag == entity.semantic_tag
        assert model.file_mode == entity.file_mode


class TestQuestionnaireMapping:
    """Tests para mapeo de Questionnaire."""
    
    def test_questionnaire_model_to_entity(self):
        """Test conversión de modelo a entidad."""
        # Crear modelo mock
        model = QuestionnaireModel()
        model.id = uuid4()
        model.title = "Cuestionario de Prueba"
        model.version = "1.0"
        model.timezone = "UTC"
        
        # Mock para questions.all()
        model.questions = type('MockManager', (), {
            'all': lambda: type('MockQuerySet', (), {
                'order_by': lambda field: []
            })()
        })()
        
        # Convertir a entidad
        entity = questionnaire_model_to_entity(model)
        
        # Verificar mapeo
        assert entity.id == model.id
        assert entity.title == model.title
        assert entity.version == model.version
        assert entity.timezone == model.timezone
        assert entity.questions == []
    
    def test_questionnaire_entity_to_model(self):
        """Test conversión de entidad a modelo."""
        # Crear entidad
        entity = QuestionnaireEntity(
            id=uuid4(),
            title="Cuestionario de Entrada",
            version="2.0",
            timezone="America/Lima",
            questions=[]
        )
        
        # Convertir a modelo
        model = questionnaire_entity_to_model(entity)
        
        # Verificar mapeo
        assert model.id == entity.id
        assert model.title == entity.title
        assert model.version == entity.version
        assert model.timezone == entity.timezone