"""
Serializadores manuales que trabajan directamente con entidades de dominio.
Estos serializadores no dependen de modelos Django y siguen los principios de Clean Architecture.
"""
from __future__ import annotations

from typing import Optional, Any, Dict, List
from uuid import UUID
from datetime import datetime

from rest_framework import serializers

from app.domain.entities import Submission, Answer, Question, Choice, Questionnaire


# =============================================================================
# SERIALIZERS DE LECTURA BASADOS EN ENTIDADES DE DOMINIO
# =============================================================================

class DomainChoiceReadSerializer(serializers.Serializer):
    """Serializer de lectura para entidades Choice del dominio."""
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    branch_to = serializers.UUIDField(read_only=True, allow_null=True)

    def to_representation(self, instance: Choice) -> Dict[str, Any]:
        """Convierte una entidad Choice a representación JSON."""
        return {
            'id': instance.id,
            'text': instance.text,
            'branch_to': instance.branch_to,
        }


class DomainQuestionReadSerializer(serializers.Serializer):
    """Serializer de lectura para entidades Question del dominio."""
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    choices = DomainChoiceReadSerializer(many=True, read_only=True, allow_null=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)
    file_mode = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance: Question) -> Dict[str, Any]:
        """Convierte una entidad Question a representación JSON."""
        choices_data = None
        if instance.choices:
            choices_data = [
                DomainChoiceReadSerializer().to_representation(choice)
                for choice in instance.choices
            ]

        return {
            'id': instance.id,
            'text': instance.text,
            'type': instance.type,
            'required': instance.required,
            'order': instance.order,
            'choices': choices_data,
            'semantic_tag': instance.semantic_tag,
            'file_mode': instance.file_mode,
        }


class DomainQuestionnaireReadSerializer(serializers.Serializer):
    """Serializer de lectura para entidades Questionnaire del dominio."""
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    timezone = serializers.CharField(read_only=True)
    questions = DomainQuestionReadSerializer(many=True, read_only=True)

    def to_representation(self, instance: Questionnaire) -> Dict[str, Any]:
        """Convierte una entidad Questionnaire a representación JSON."""
        questions_data = [
            DomainQuestionReadSerializer().to_representation(question)
            for question in instance.questions
        ]

        return {
            'id': instance.id,
            'title': instance.title,
            'version': instance.version,
            'timezone': instance.timezone,
            'questions': questions_data,
        }


class DomainAnswerReadSerializer(serializers.Serializer):
    """
    Serializer de lectura para entidades Answer del dominio.
    Proporciona una representación enriquecida compatible con el frontend.
    """
    id = serializers.UUIDField(read_only=True)
    submission_id = serializers.UUIDField(read_only=True)
    question_id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_text = serializers.CharField(read_only=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_file_path = serializers.CharField(read_only=True, allow_null=True)
    ocr_meta = serializers.JSONField(read_only=True)
    meta = serializers.JSONField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)

    # Campos enriquecidos para compatibilidad con frontend
    answer_file = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    answer_choice = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        """Inicializa el serializer con contexto opcional para enriquecimiento."""
        super().__init__(*args, **kwargs)
        # Contexto opcional para enriquecer con datos relacionados
        self._question_cache = {}
        self._choice_cache = {}

    def to_representation(self, instance: Answer) -> Dict[str, Any]:
        """Convierte una entidad Answer a representación JSON."""
        data = {
            'id': instance.id,
            'submission_id': instance.submission_id,
            'question_id': instance.question_id,
            'user_id': instance.user_id,
            'answer_text': instance.answer_text,
            'answer_choice_id': instance.answer_choice_id,
            'answer_file_path': instance.answer_file_path,
            'ocr_meta': instance.ocr_meta,
            'meta': instance.meta,
            'timestamp': instance.timestamp,
        }

        # Agregar campos enriquecidos si hay contexto disponible
        data['answer_file'] = self.get_answer_file(instance)
        data['question'] = self.get_question(instance)
        data['answer_choice'] = self.get_answer_choice(instance)

        return data

    def get_answer_file(self, obj: Answer) -> Optional[str]:
        """
        Genera URL segura para el archivo de respuesta.
        En una implementación completa, esto debería usar el servicio de storage.
        """
        if not obj.answer_file_path:
            return None
        
        # Por ahora retornamos la ruta, en implementación completa
        # se debería usar el servicio de storage para generar URL segura
        request = self.context.get('request')
        if request and obj.answer_file_path:
            try:
                # Generar URL relativa para media protegida
                return f"/api/media/{obj.answer_file_path}"
            except Exception:
                pass
        
        return obj.answer_file_path

    def get_question(self, obj: Answer) -> Optional[Dict[str, Any]]:
        """
        Retorna información de la pregunta asociada.
        En implementación completa, esto se obtendría del repositorio.
        """
        # En una implementación completa, aquí se consultaría el repositorio
        # de preguntas para obtener los datos enriquecidos
        question_data = self.context.get('questions_data', {}).get(str(obj.question_id))
        if question_data:
            return {
                'id': str(obj.question_id),
                'text': question_data.get('text', ''),
                'type': question_data.get('type', ''),
                'semantic_tag': question_data.get('semantic_tag'),
            }
        
        return {
            'id': str(obj.question_id),
            'text': '',
            'type': '',
            'semantic_tag': None,
        }

    def get_answer_choice(self, obj: Answer) -> Optional[Dict[str, Any]]:
        """
        Retorna información de la opción de respuesta seleccionada.
        En implementación completa, esto se obtendría del repositorio.
        """
        if not obj.answer_choice_id:
            return None
        
        # En una implementación completa, aquí se consultaría el repositorio
        # de opciones para obtener los datos enriquecidos
        choice_data = self.context.get('choices_data', {}).get(str(obj.answer_choice_id))
        if choice_data:
            return {
                'id': str(obj.answer_choice_id),
                'text': choice_data.get('text', ''),
            }
        
        return {
            'id': str(obj.answer_choice_id),
            'text': '',
        }


class DomainSubmissionReadSerializer(serializers.Serializer):
    """
    Serializer de lectura para entidades Submission del dominio.
    Proporciona representación completa compatible con el frontend.
    """
    id = serializers.UUIDField(read_only=True)
    questionnaire_id = serializers.UUIDField(read_only=True)
    tipo_fase = serializers.CharField(read_only=True)
    regulador_id = serializers.UUIDField(read_only=True, allow_null=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    finalizado = serializers.BooleanField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)

    # Campos enriquecidos
    questionnaire = serializers.SerializerMethodField()
    questionnaire_title = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    def to_representation(self, instance: Submission) -> Dict[str, Any]:
        """Convierte una entidad Submission a representación JSON."""
        data = {
            'id': instance.id,
            'questionnaire_id': instance.questionnaire_id,
            'questionnaire': instance.questionnaire_id,  # Compatibilidad con frontend
            'tipo_fase': instance.tipo_fase,
            'regulador_id': instance.regulador_id,
            'placa_vehiculo': instance.placa_vehiculo,
            'finalizado': instance.finalizado,
            'fecha_creacion': instance.fecha_creacion,
            'fecha_cierre': instance.fecha_cierre,
        }

        # Agregar campos enriquecidos si hay contexto disponible
        data['questionnaire_title'] = self.get_questionnaire_title(instance)
        data['answers'] = self.get_answers(instance)

        return data

    def get_questionnaire_title(self, obj: Submission) -> str:
        """
        Retorna el título del cuestionario asociado.
        En implementación completa, esto se obtendría del repositorio.
        """
        questionnaire_data = self.context.get('questionnaires_data', {}).get(str(obj.questionnaire_id))
        if questionnaire_data:
            return questionnaire_data.get('title', '')
        return ''

    def get_answers(self, obj: Submission) -> List[Dict[str, Any]]:
        """
        Retorna las respuestas asociadas al submission.
        En implementación completa, esto se obtendría del repositorio.
        """
        answers_data = self.context.get('answers_data', {}).get(str(obj.id), [])
        if answers_data:
            return [
                DomainAnswerReadSerializer(context=self.context).to_representation(answer)
                for answer in answers_data
            ]
        return []


# =============================================================================
# SERIALIZERS DE RESPUESTA PARA CASOS DE USO ESPECÍFICOS
# =============================================================================

class DomainSubmissionListSerializer(serializers.Serializer):
    """
    Serializer simplificado para listado de submissions.
    Solo incluye campos esenciales para mejorar performance.
    """
    id = serializers.UUIDField(read_only=True)
    questionnaire_id = serializers.UUIDField(read_only=True)
    questionnaire_title = serializers.SerializerMethodField()
    tipo_fase = serializers.CharField(read_only=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    finalizado = serializers.BooleanField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)

    def to_representation(self, instance: Submission) -> Dict[str, Any]:
        """Convierte una entidad Submission a representación simplificada."""
        return {
            'id': instance.id,
            'questionnaire_id': instance.questionnaire_id,
            'questionnaire': instance.questionnaire_id,  # Compatibilidad
            'questionnaire_title': self.get_questionnaire_title(instance),
            'tipo_fase': instance.tipo_fase,
            'placa_vehiculo': instance.placa_vehiculo,
            'finalizado': instance.finalizado,
            'fecha_creacion': instance.fecha_creacion,
            'fecha_cierre': instance.fecha_cierre,
        }

    def get_questionnaire_title(self, obj: Submission) -> str:
        """Retorna el título del cuestionario desde el contexto."""
        questionnaire_data = self.context.get('questionnaires_data', {}).get(str(obj.questionnaire_id))
        if questionnaire_data:
            return questionnaire_data.get('title', '')
        return ''


class DomainQuestionDetailSerializer(serializers.Serializer):
    """
    Serializer para detalle completo de una pregunta.
    Incluye todas las opciones y metadatos necesarios.
    """
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    choices = DomainChoiceReadSerializer(many=True, read_only=True, allow_null=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)
    file_mode = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance: Question) -> Dict[str, Any]:
        """Convierte una entidad Question a representación detallada."""
        choices_data = []
        if instance.choices:
            for choice in instance.choices:
                choices_data.append(DomainChoiceReadSerializer().to_representation(choice))

        return {
            'id': instance.id,
            'text': instance.text,
            'type': instance.type,
            'required': instance.required,
            'order': instance.order,
            'choices': choices_data,
            'semantic_tag': instance.semantic_tag,
            'file_mode': instance.file_mode,
        }


# =============================================================================
# SERIALIZERS PARA CASOS DE USO ESPECÍFICOS
# =============================================================================

class SaveAndAdvanceEntityResponseSerializer(serializers.Serializer):
    """
    Serializer de respuesta para el caso de uso Save and Advance.
    Trabaja directamente con entidades de dominio.
    """
    saved_answer = serializers.SerializerMethodField()
    next_question_id = serializers.UUIDField(allow_null=True, read_only=True)
    next_question = serializers.SerializerMethodField()
    is_finished = serializers.BooleanField(read_only=True)
    derived_updates = serializers.JSONField(read_only=True)
    warnings = serializers.ListField(child=serializers.CharField(), read_only=True)

    def get_saved_answer(self, obj) -> Optional[Dict[str, Any]]:
        """Serializa la respuesta guardada usando el serializer de entidades."""
        saved_answer = getattr(obj, 'saved_answer', None)
        if saved_answer is None:
            return None
        
        return DomainAnswerReadSerializer(context=self.context).to_representation(saved_answer)

    def get_next_question(self, obj) -> Optional[Dict[str, Any]]:
        """Serializa la siguiente pregunta usando el serializer de entidades."""
        next_question = getattr(obj, 'next_question', None)
        if next_question is None:
            return None
        
        return DomainQuestionDetailSerializer().to_representation(next_question)


class VerificationEntityResponseSerializer(serializers.Serializer):
    """
    Serializer de respuesta para verificación OCR.
    Independiente de modelos Django.
    """
    ocr_raw = serializers.CharField(read_only=True)
    placa = serializers.CharField(read_only=True, allow_null=True)
    precinto = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    valido = serializers.BooleanField(read_only=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el resultado de verificación a representación JSON."""
        return {
            'ocr_raw': instance.get('ocr_raw', ''),
            'placa': instance.get('placa'),
            'precinto': instance.get('precinto'),
            'contenedor': instance.get('contenedor'),
            'valido': instance.get('valido', False),
            'semantic_tag': instance.get('semantic_tag'),
        }


class QuestionnaireListEntitySerializer(serializers.Serializer):
    """
    Serializer simplificado para listado de cuestionarios.
    Solo incluye campos esenciales.
    """
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)

    def to_representation(self, instance: Questionnaire) -> Dict[str, Any]:
        """Convierte una entidad Questionnaire a representación simplificada."""
        return {
            'id': instance.id,
            'title': instance.title,
            'version': instance.version,
        }

# =============================================================================
# SERIALIZERS DE ENTRADA BASADOS EN COMANDOS DE DOMINIO
# =============================================================================

class CreateSubmissionCommandSerializer(serializers.Serializer):
    """
    Serializer para comando de creación de submission.
    Trabaja directamente con comandos de dominio.
    """
    questionnaire_id = serializers.UUIDField()
    tipo_fase = serializers.ChoiceField(choices=["entrada", "salida"])
    regulador_id = serializers.UUIDField(required=False, allow_null=True)
    placa_vehiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        """Valida estructura básica del comando."""
        # Normalizar placa_vehiculo
        placa = attrs.get("placa_vehiculo")
        if placa:
            placa = str(placa).strip()
            attrs["placa_vehiculo"] = placa if placa else None
        else:
            attrs["placa_vehiculo"] = None

        return attrs

    def to_command(self):
        """Convierte los datos validados a un comando de dominio."""
        from app.application.commands import CreateSubmissionCommand
        return CreateSubmissionCommand(**self.validated_data)


class SaveAnswerCommandSerializer(serializers.Serializer):
    """
    Serializer para comando de guardado de respuesta.
    Trabaja directamente con comandos de dominio.
    """
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file_path = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ocr_meta = serializers.DictField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, allow_null=True)

    def validate(self, attrs):
        """Valida estructura básica del comando."""
        # Normalizar texto vacío -> None
        text = attrs.get("answer_text")
        if text:
            text = str(text).strip()
            attrs["answer_text"] = text if text else None
        else:
            attrs["answer_text"] = None

        # Verificar que hay al menos una respuesta
        has_text = bool(attrs["answer_text"])
        has_choice = attrs.get("answer_choice_id") is not None
        has_file = bool(attrs.get("answer_file_path"))

        if not (has_text or has_choice or has_file):
            raise serializers.ValidationError(
                {"non_field_errors": ["Debes enviar al menos uno de: answer_text, answer_choice_id o answer_file_path."]}
            )

        return attrs

    def to_command(self):
        """Convierte los datos validados a un comando de dominio."""
        from app.application.commands import SaveAnswerCommand
        return SaveAnswerCommand(**self.validated_data)


# =============================================================================
# SERIALIZERS PARA CASOS DE USO ESPECÍFICOS CON ENTIDADES
# =============================================================================

class EntityBasedSubmissionDetailSerializer(serializers.Serializer):
    """
    Serializer para detalle completo de submission usando entidades.
    Incluye todas las respuestas y datos relacionados.
    """
    submission = DomainSubmissionReadSerializer()
    answers = DomainAnswerReadSerializer(many=True)
    questionnaire = DomainQuestionnaireReadSerializer()

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el conjunto de entidades a representación JSON."""
        return {
            'submission': DomainSubmissionReadSerializer(context=self.context).to_representation(
                instance.get('submission')
            ),
            'answers': [
                DomainAnswerReadSerializer(context=self.context).to_representation(answer)
                for answer in instance.get('answers', [])
            ],
            'questionnaire': DomainQuestionnaireReadSerializer().to_representation(
                instance.get('questionnaire')
            ) if instance.get('questionnaire') else None,
        }


class EntityBasedHistoryItemSerializer(serializers.Serializer):
    """
    Serializer para items del historial usando entidades.
    """
    regulador_id = serializers.UUIDField(read_only=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    ultima_fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    fase1 = DomainSubmissionReadSerializer(read_only=True, allow_null=True)
    fase2 = DomainSubmissionReadSerializer(read_only=True, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el item del historial a representación JSON."""
        return {
            'regulador_id': instance.get('regulador_id'),
            'placa_vehiculo': instance.get('placa_vehiculo'),
            'contenedor': instance.get('contenedor'),
            'ultima_fecha_cierre': instance.get('ultima_fecha_cierre'),
            'fase1': DomainSubmissionReadSerializer(context=self.context).to_representation(
                instance.get('fase1')
            ) if instance.get('fase1') else None,
            'fase2': DomainSubmissionReadSerializer(context=self.context).to_representation(
                instance.get('fase2')
            ) if instance.get('fase2') else None,
        }


# =============================================================================
# SERIALIZERS DE RESPUESTA PARA APIS ESPECÍFICAS
# =============================================================================

class EntityBasedQuestionDetailResponseSerializer(serializers.Serializer):
    """
    Serializer de respuesta para detalle de pregunta usando entidades.
    """
    question = DomainQuestionDetailSerializer()
    
    def to_representation(self, instance) -> Dict[str, Any]:
        """Convierte la entidad Question a respuesta de API."""
        return DomainQuestionDetailSerializer().to_representation(instance)


class EntityBasedSubmissionListResponseSerializer(serializers.Serializer):
    """
    Serializer de respuesta para listado de submissions usando entidades.
    """
    results = DomainSubmissionListSerializer(many=True)
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el resultado paginado a representación JSON."""
        return {
            'results': [
                DomainSubmissionListSerializer(context=self.context).to_representation(submission)
                for submission in instance.get('results', [])
            ],
            'count': instance.get('count', 0),
            'next': instance.get('next'),
            'previous': instance.get('previous'),
        }


class EntityBasedActorSerializer(serializers.Serializer):
    """
    Serializer para entidades Actor del dominio.
    """
    id = serializers.UUIDField(read_only=True)
    tipo = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True, allow_null=True)
    activo = serializers.BooleanField(read_only=True)

    def to_representation(self, instance) -> Dict[str, Any]:
        """Convierte una entidad Actor a representación JSON."""
        return {
            'id': getattr(instance, 'id', None),
            'tipo': getattr(instance, 'tipo', None),
            'nombre': getattr(instance, 'nombre', None),
            'documento': getattr(instance, 'documento', None),
            'activo': getattr(instance, 'activo', True),
        }


# =============================================================================
# UTILIDADES PARA MIGRACIÓN GRADUAL
# =============================================================================

class HybridSerializer:
    """
    Clase base para serializers que pueden trabajar tanto con modelos Django
    como con entidades de dominio durante la migración.
    """
    
    @staticmethod
    def is_django_model(obj) -> bool:
        """Verifica si el objeto es un modelo Django."""
        return hasattr(obj, '_state') and hasattr(obj._state, 'db')
    
    @staticmethod
    def is_domain_entity(obj) -> bool:
        """Verifica si el objeto es una entidad de dominio (dataclass)."""
        return hasattr(obj, '__dataclass_fields__')
    
    @staticmethod
    def get_field_value(obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default


class MigrationCompatibleSubmissionSerializer(HybridSerializer, serializers.Serializer):
    """
    Serializer compatible que puede manejar tanto modelos como entidades
    durante la migración a Clean Architecture.
    """
    
    def to_representation(self, instance):
        """Convierte tanto modelos como entidades a representación JSON."""
        if self.is_domain_entity(instance):
            # Usar serializer de entidades
            return DomainSubmissionReadSerializer(context=self.context).to_representation(instance)
        else:
            # Convert model to entity first, then serialize
            # This ensures we only work with domain entities
            raise ValueError("MigrationCompatibleSubmissionSerializer should only receive domain entities. "
                           "Convert models to entities in the repository layer.")

# =============================================================================
# ADMIN SERIALIZERS FOR DOMAIN ENTITIES
# =============================================================================

class DomainChoiceSerializer(serializers.Serializer):
    """Serializer for Choice domain entities used in admin interfaces."""
    id = serializers.UUIDField()
    text = serializers.CharField()
    branch_to = serializers.UUIDField(allow_null=True, required=False)


class DomainQuestionSerializer(serializers.Serializer):
    """Serializer for Question domain entities used in admin interfaces."""
    id = serializers.UUIDField()
    text = serializers.CharField()
    type = serializers.CharField()
    required = serializers.BooleanField()
    order = serializers.IntegerField()
    choices = DomainChoiceSerializer(many=True, required=False, allow_null=True)
    semantic_tag = serializers.CharField(required=False, allow_null=True)
    file_mode = serializers.CharField(required=False, allow_null=True)


class DomainQuestionnaireSerializer(serializers.Serializer):
    """Serializer for Questionnaire domain entities used in admin interfaces."""
    id = serializers.UUIDField()
    title = serializers.CharField()
    version = serializers.CharField()
    timezone = serializers.CharField()
    questions = DomainQuestionSerializer(many=True)