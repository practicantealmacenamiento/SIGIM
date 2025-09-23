from __future__ import annotations

from typing import Optional, Any, Dict
from uuid import UUID
from urllib.parse import urljoin

from rest_framework import serializers
from django.conf import settings
from django.core.files.storage import default_storage

from app.infrastructure.models import (
    Questionnaire, Question, Choice, Answer, Submission, Actor
)

# Usa las reglas unificadas (placa/precinto/contenedor)
from app.domain.rules import normalizar_placa as _normalizar_placa_reglas


# --------------------------- helpers --------------------------- #
def _placa_or_none(txt: Optional[str]) -> Optional[str]:
    if not txt:
        return None
    val = _normalizar_placa_reglas(txt)
    return None if val == "NO_DETECTADA" else val


def _build_abs_url(request, relative_url: str) -> str:
    if not relative_url:
        return relative_url
    if request:
        try:
            return request.build_absolute_uri(relative_url)
        except Exception:
            pass
    return relative_url


# ----------------------------------------------------------------------
# SERIALIZER PARA GUARDAR RESPUESTAS (Input clásico)
# ----------------------------------------------------------------------
class GuardarRespuestaSerializer(serializers.Serializer):
    """
    Serializer manual para guardar respuestas de usuario.
    No depende de modelos Django y valida usando servicios de dominio.
    """
    question_id = serializers.UUIDField()
    submission_id = serializers.UUIDField()

    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file = serializers.FileField(required=False, allow_null=True)

    # Soporte para catálogo de actores
    actor_id = serializers.UUIDField(required=False, allow_null=True)

    # Metadatos opcionales
    ocr_meta = serializers.DictField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, allow_null=True)

    def validate(self, attrs):
        """
        Valida que venga al menos una respuesta y que los datos sean consistentes.
        Usa servicios de dominio en lugar de acceso directo a modelos.
        """
        # Normalizar texto vacío -> None
        txt = attrs.get("answer_text")
        if isinstance(txt, str):
            txt = txt.strip()
            attrs["answer_text"] = txt if txt else None

        # Verificar que hay al menos una respuesta
        req = self.context.get("request")
        files = []
        if req:
            files = req.FILES.getlist("answer_file") or req.FILES.getlist("answer_files")

        has_payload = bool(
            attrs.get("answer_text")
            or attrs.get("answer_choice_id")
            or attrs.get("answer_file")
            or files
            or attrs.get("actor_id")
        )
        
        if not has_payload:
            raise serializers.ValidationError(
                {"non_field_errors": ["Debes enviar una respuesta (texto, opción, archivo(s) o actor)."]}
            )

        # Validaciones de dominio se delegan a los servicios de aplicación
        # El serializer solo valida formato y estructura básica
        
        # Validar que los UUIDs sean válidos
        self._validate_uuid_field(attrs, "question_id")
        self._validate_uuid_field(attrs, "submission_id")
        
        if attrs.get("answer_choice_id"):
            self._validate_uuid_field(attrs, "answer_choice_id")
        
        if attrs.get("actor_id"):
            self._validate_uuid_field(attrs, "actor_id")

        # Validar metadatos sean diccionarios válidos
        if attrs.get("ocr_meta") and not isinstance(attrs["ocr_meta"], dict):
            raise serializers.ValidationError({"ocr_meta": ["Debe ser un diccionario válido."]})
        
        if attrs.get("meta") and not isinstance(attrs["meta"], dict):
            raise serializers.ValidationError({"meta": ["Debe ser un diccionario válido."]})

        return attrs

    def _validate_uuid_field(self, attrs, field_name):
        """Valida que un campo UUID tenga formato válido."""
        value = attrs.get(field_name)
        if value:
            try:
                from uuid import UUID
                UUID(str(value))
            except (ValueError, TypeError):
                raise serializers.ValidationError({field_name: ["Formato de UUID inválido."]})

    def validate_answer_file(self, value):
        """Valida archivos de respuesta."""
        if not value:
            return value
            
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        max_size = 10 * 1024 * 1024  # 10 MB
        
        content_type = getattr(value, "content_type", None)
        if content_type not in allowed_types:
            raise serializers.ValidationError("Solo se permiten archivos JPG, PNG o PDF.")
        
        if value.size > max_size:
            raise serializers.ValidationError("El archivo no debe superar los 10MB.")
        
        return value


# ----------------------------------------------------------------------
# READ – manuales sobre modelos
# ----------------------------------------------------------------------
class ActorModelSerializer(serializers.Serializer):
    """
    Serializer manual para actores.
    No depende de ModelSerializer y maneja tanto modelos como entidades.
    """
    id = serializers.UUIDField(read_only=True)
    tipo = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True, allow_null=True)
    activo = serializers.BooleanField(read_only=True)

    def to_representation(self, instance):
        """
        Convierte el objeto (modelo o entidad) a representación JSON.
        """
        if instance is None:
            return None
            
        return {
            'id': self._get_field_value(instance, 'id'),
            'tipo': self._get_field_value(instance, 'tipo'),
            'nombre': self._get_field_value(instance, 'nombre'),
            'documento': self._get_field_value(instance, 'documento'),
            'activo': self._get_field_value(instance, 'activo', True),  # Default True
        }

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default


class ChoiceModelSerializer(serializers.Serializer):
    """
    Serializer manual para opciones de preguntas.
    No depende de ModelSerializer y maneja tanto modelos como entidades.
    """
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    branch_to = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """Convierte el objeto (modelo o entidad) a representación JSON."""
        return {
            'id': self._get_field_value(instance, 'id'),
            'text': self._get_field_value(instance, 'text'),
            'branch_to': self.get_branch_to(instance),
        }

    def get_branch_to(self, obj):
        """Retorna el ID de la pregunta de ramificación."""
        # Intentar desde branch_to_id directo
        branch_to_id = self._get_field_value(obj, "branch_to_id")
        if branch_to_id:
            return str(branch_to_id)
        
        # Intentar desde relación branch_to
        branch_to = self._get_field_value(obj, "branch_to")
        if branch_to:
            branch_id = getattr(branch_to, "id", None)
            return str(branch_id) if branch_id else None
        
        return None

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default


class QuestionModelSerializer(serializers.Serializer):
    """
    Serializer manual para preguntas.
    No depende de ModelSerializer y maneja tanto modelos como entidades.
    """
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    choices = serializers.SerializerMethodField()
    file_mode = serializers.CharField(read_only=True, allow_null=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance):
        """Convierte el objeto (modelo o entidad) a representación JSON."""
        return {
            'id': self._get_field_value(instance, 'id'),
            'text': self._get_field_value(instance, 'text'),
            'type': self._get_field_value(instance, 'type'),
            'required': self._get_field_value(instance, 'required', False),
            'order': self._get_field_value(instance, 'order', 0),
            'choices': self.get_choices(instance),
            'file_mode': self._get_field_value(instance, 'file_mode'),
            'semantic_tag': self._get_field_value(instance, 'semantic_tag'),
        }

    def get_choices(self, obj):
        """Retorna las opciones de la pregunta."""
        choices = self._get_field_value(obj, 'choices')
        if choices is None:
            return []
        
        # Si es una relación de Django (QuerySet o Manager)
        if hasattr(choices, 'all'):
            choices = choices.all()
        
        # Si es una lista, tupla o QuerySet (entidades de dominio o modelos Django)
        if isinstance(choices, (list, tuple)) or hasattr(choices, '__iter__'):
            return [
                ChoiceModelSerializer().to_representation(choice)
                for choice in choices
            ]
        
        return []

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default


class QuestionnaireModelSerializer(serializers.Serializer):
    """
    Serializer manual para cuestionarios.
    No depende de ModelSerializer y maneja tanto modelos como entidades.
    """
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    timezone = serializers.CharField(read_only=True)
    questions = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """Convierte el objeto (modelo o entidad) a representación JSON."""
        return {
            'id': self._get_field_value(instance, 'id'),
            'title': self._get_field_value(instance, 'title'),
            'version': self._get_field_value(instance, 'version'),
            'timezone': self._get_field_value(instance, 'timezone'),
            'questions': self.get_questions(instance),
        }

    def get_questions(self, obj):
        """Retorna las preguntas del cuestionario."""
        questions = self._get_field_value(obj, 'questions')
        if questions is None:
            return []
        
        # Si es una relación de Django (QuerySet o Manager)
        if hasattr(questions, 'all'):
            questions = questions.all()
        
        # Si es una lista (entidades de dominio)
        if isinstance(questions, (list, tuple)):
            return [
                QuestionModelSerializer().to_representation(question)
                for question in questions
            ]
        
        return []

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default


class AnswerReadSerializer(serializers.Serializer):
    """
    Serializer manual para lectura de respuestas.
    No depende de ModelSerializer y trabaja con datos normalizados.
    """
    id = serializers.UUIDField(read_only=True)
    submission_id = serializers.UUIDField(read_only=True)
    question_id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_text = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_file_path = serializers.CharField(read_only=True, allow_null=True)
    timestamp = serializers.DateTimeField(read_only=True)

    # Estructura enriquecida esperada por el front
    question = serializers.SerializerMethodField()
    answer_choice = serializers.SerializerMethodField()
    answer_file = serializers.SerializerMethodField()

    # Campos aplanados útiles para la UI/búsqueda (compatibilidad)
    question_text = serializers.SerializerMethodField()
    question_type = serializers.SerializerMethodField()
    question_tag = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """
        Convierte el objeto (modelo o entidad) a representación JSON.
        Maneja tanto modelos Django como entidades de dominio.
        """
        # Extraer datos básicos independientemente del tipo de objeto
        data = {
            'id': self._get_field_value(instance, 'id'),
            'submission_id': self._get_field_value(instance, 'submission_id'),
            'question_id': self._get_field_value(instance, 'question_id'),
            'user_id': self._get_field_value(instance, 'user_id'),
            'answer_text': self._get_field_value(instance, 'answer_text'),
            'answer_choice_id': self._get_field_value(instance, 'answer_choice_id'),
            'answer_file_path': self._get_field_value(instance, 'answer_file_path') or self._get_file_path(instance),
            'timestamp': self._get_field_value(instance, 'timestamp'),
        }

        # Agregar campos enriquecidos
        data.update({
            'question': self.get_question(instance),
            'answer_choice': self.get_answer_choice(instance),
            'answer_file': self.get_answer_file(instance),
            'question_text': self.get_question_text(instance),
            'question_type': self.get_question_type(instance),
            'question_tag': self.get_question_tag(instance),
        })

        return data

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default

    def _get_file_path(self, obj):
        """Extrae ruta de archivo desde diferentes fuentes."""
        # Para modelos Django con FileField
        answer_file = self._get_field_value(obj, 'answer_file')
        if answer_file and hasattr(answer_file, 'name'):
            return answer_file.name
        return None

    def get_question(self, obj):
        """Retorna información de la pregunta asociada."""
        question = self._get_field_value(obj, "question")
        if not question:
            # Si no hay relación cargada, usar datos del contexto o crear estructura básica
            question_id = self._get_field_value(obj, "question_id")
            question_data = self.context.get('questions_data', {}).get(str(question_id), {})
            return {
                "id": str(question_id) if question_id else None,
                "text": question_data.get('text', ''),
                "type": question_data.get('type', ''),
                "semantic_tag": question_data.get('semantic_tag'),
            }
        
        # Compatibilidad: algunos modelos usan "label"
        text = getattr(question, "text", None) or getattr(question, "label", None)
        return {
            "id": str(getattr(question, "id")),
            "text": text,
            "type": getattr(question, "type", None),
            "semantic_tag": getattr(question, "semantic_tag", None),
        }

    def get_answer_choice(self, obj):
        """Retorna información de la opción de respuesta seleccionada."""
        choice = self._get_field_value(obj, "answer_choice")
        if not choice:
            # Si no hay relación cargada, usar datos del contexto
            choice_id = self._get_field_value(obj, "answer_choice_id")
            if not choice_id:
                return None
            
            choice_data = self.context.get('choices_data', {}).get(str(choice_id), {})
            return {
                "id": str(choice_id),
                "text": choice_data.get('text', ''),
            }
        
        # El front espera "text" (no "label")
        text = getattr(choice, "text", None) or getattr(choice, "label", None) or getattr(choice, "name", None)
        return {"id": str(getattr(choice, "id")), "text": text}

    def get_answer_file(self, obj):
        """Genera URL segura para el archivo de respuesta."""
        # Primero intentar obtener desde answer_file_path (entidades)
        file_path = self._get_field_value(obj, 'answer_file_path')
        
        # Si no existe, intentar desde answer_file (modelos Django)
        if not file_path:
            answer_file = self._get_field_value(obj, "answer_file")
            if answer_file and hasattr(answer_file, 'name'):
                file_path = answer_file.name
        
        if not file_path:
            return None
        
        # Generar URL segura con autenticación
        try:
            from app.infrastructure.storage import get_secure_media_url
            return get_secure_media_url(file_path)
        except Exception:
            # Fallback: generar URL relativa para media protegida
            request = self.context.get('request')
            if request:
                return f"/api/media/{file_path}"
            return file_path

    def get_question_text(self, obj):
        """Retorna el texto de la pregunta (campo aplanado)."""
        question_info = self.get_question(obj)
        return question_info.get('text', '') if question_info else ''

    def get_question_type(self, obj):
        """Retorna el tipo de la pregunta (campo aplanado)."""
        question_info = self.get_question(obj)
        return question_info.get('type', '') if question_info else ''

    def get_question_tag(self, obj):
        """Retorna el semantic_tag de la pregunta (campo aplanado)."""
        question_info = self.get_question(obj)
        return question_info.get('semantic_tag') if question_info else None


# ----------------------------------------------------------------------
# WRITE – básicos (no OCR)
# ----------------------------------------------------------------------
class AnswerWriteSerializer(serializers.Serializer):
    """
    Serializer manual para escritura de respuestas.
    No depende de modelos Django y valida estructura básica.
    """
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)

    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file = serializers.FileField(required=False, allow_null=True)

    ocr_meta = serializers.JSONField(required=False, allow_null=True)
    meta = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        """Valida estructura básica de la respuesta."""
        # Normalizar texto
        text = (attrs.get("answer_text") or "").strip()
        attrs["answer_text"] = text if text else None

        # Verificar que hay al menos una respuesta
        has_text = bool(attrs["answer_text"])
        has_choice = attrs.get("answer_choice_id") is not None
        has_file = attrs.get("answer_file") is not None

        if not (has_text or has_choice or has_file):
            raise serializers.ValidationError(
                {"non_field_errors": ["Debes enviar al menos uno de: answer_text, answer_choice_id o answer_file."]}
            )

        # Validar UUIDs
        self._validate_uuid_field(attrs, "submission_id")
        self._validate_uuid_field(attrs, "question_id")
        
        if attrs.get("user_id"):
            self._validate_uuid_field(attrs, "user_id")
        
        if attrs.get("answer_choice_id"):
            self._validate_uuid_field(attrs, "answer_choice_id")

        # Validar metadatos
        if attrs.get("ocr_meta") and not isinstance(attrs["ocr_meta"], dict):
            raise serializers.ValidationError({"ocr_meta": ["Debe ser un diccionario válido."]})
        
        if attrs.get("meta") and not isinstance(attrs["meta"], dict):
            raise serializers.ValidationError({"meta": ["Debe ser un diccionario válido."]})

        return attrs

    def _validate_uuid_field(self, attrs, field_name):
        """Valida que un campo UUID tenga formato válido."""
        value = attrs.get(field_name)
        if value:
            try:
                from uuid import UUID
                UUID(str(value))
            except (ValueError, TypeError):
                raise serializers.ValidationError({field_name: ["Formato de UUID inválido."]})


class SubmissionCreateSerializer(serializers.Serializer):
    """
    Serializer manual para creación de submissions.
    No depende de modelos Django y valida estructura básica.
    """
    questionnaire = serializers.UUIDField(required=False)  # Compatibilidad hacia atrás
    questionnaire_id = serializers.UUIDField(required=False)  # Formato preferido
    tipo_fase = serializers.ChoiceField(choices=["entrada", "salida"])
    regulador_id = serializers.UUIDField(required=False, allow_null=True)
    placa_vehiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        """Valida estructura básica del submission."""
        # Normalizar questionnaire_id (puede venir como 'questionnaire' o 'questionnaire_id')
        questionnaire_id = attrs.get("questionnaire") or attrs.get("questionnaire_id")
        if not questionnaire_id:
            raise serializers.ValidationError({"questionnaire": ["Este campo es obligatorio."]})
        
        # Validar UUID del cuestionario
        try:
            from uuid import UUID
            UUID(str(questionnaire_id))
            attrs["questionnaire_id"] = questionnaire_id
        except (ValueError, TypeError):
            raise serializers.ValidationError({"questionnaire": ["Formato de UUID inválido."]})

        # Remover el campo 'questionnaire' para evitar conflictos
        if "questionnaire" in attrs:
            del attrs["questionnaire"]

        # Validar regulador_id si se proporciona
        if attrs.get("regulador_id"):
            try:
                from uuid import UUID
                UUID(str(attrs["regulador_id"]))
            except (ValueError, TypeError):
                raise serializers.ValidationError({"regulador_id": ["Formato de UUID inválido."]})

        # Normalizar placa_vehiculo
        placa = attrs.get("placa_vehiculo")
        if placa:
            placa = str(placa).strip()
            attrs["placa_vehiculo"] = placa if placa else None
        else:
            attrs["placa_vehiculo"] = None

        return attrs

# ----------------------------------------------------------------------
# Submission (modelo) con respuestas embebidas (READ)
# ----------------------------------------------------------------------
class SubmissionModelSerializer(serializers.Serializer):
    """
    Serializer manual para lectura de submissions.
    No depende de ModelSerializer y maneja tanto modelos como entidades.
    """
    id = serializers.UUIDField(read_only=True)
    questionnaire = serializers.UUIDField(read_only=True)
    questionnaire_id = serializers.UUIDField(read_only=True)
    questionnaire_title = serializers.SerializerMethodField()
    tipo_fase = serializers.CharField(read_only=True)
    placa_vehiculo = serializers.SerializerMethodField()
    regulador_id = serializers.UUIDField(read_only=True, allow_null=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    finalizado = serializers.BooleanField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    contenedor = serializers.SerializerMethodField()
    precinto = serializers.SerializerMethodField()

    # Campos de actores
    proveedor_id = serializers.SerializerMethodField()
    transportista_id = serializers.SerializerMethodField()
    receptor_id = serializers.SerializerMethodField()
    proveedor = serializers.SerializerMethodField()
    transportista = serializers.SerializerMethodField()
    receptor = serializers.SerializerMethodField()

    # Detalle de respuestas
    answers = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """
        Convierte el objeto (modelo o entidad) a representación JSON.
        Maneja tanto modelos Django como entidades de dominio.
        """
        # Extraer questionnaire_id de diferentes fuentes
        questionnaire_id = (
            self._get_field_value(instance, 'questionnaire_id') or
            self._get_related_id(instance, 'questionnaire')
        )

        data = {
            'id': self._get_field_value(instance, 'id'),
            'questionnaire': questionnaire_id,  # Compatibilidad con frontend
            'questionnaire_id': questionnaire_id,
            'questionnaire_title': self.get_questionnaire_title(instance),
            'tipo_fase': self._get_field_value(instance, 'tipo_fase'),
            'placa_vehiculo': self.get_placa_vehiculo(instance),
            'regulador_id': self._get_field_value(instance, 'regulador_id'),
            'fecha_creacion': self._get_field_value(instance, 'fecha_creacion'),
            'finalizado': self._get_field_value(instance, 'finalizado'),
            'fecha_cierre': self._get_field_value(instance, 'fecha_cierre'),
            'contenedor': self.get_contenedor(instance),
            'precinto': self.get_precinto(instance),
            'proveedor_id': self.get_proveedor_id(instance),
            'transportista_id': self.get_transportista_id(instance),
            'receptor_id': self.get_receptor_id(instance),
            'proveedor': self.get_proveedor(instance),
            'transportista': self.get_transportista(instance),
            'receptor': self.get_receptor(instance),
            'answers': self.get_answers(instance),
        }

        return data

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default

    def _get_related_id(self, obj, relation_name):
        """Extrae ID de una relación de manera segura."""
        try:
            related = getattr(obj, relation_name, None)
            if related:
                return getattr(related, 'id', None)
        except Exception:
            pass
        return None

    def get_questionnaire_title(self, obj):
        """Retorna el título del cuestionario."""
        # Intentar desde relación cargada (modelos Django)
        questionnaire = self._get_field_value(obj, 'questionnaire')
        if questionnaire:
            return getattr(questionnaire, 'title', '')
        
        # Usar datos del contexto si están disponibles
        questionnaire_id = (
            self._get_field_value(obj, 'questionnaire_id') or
            self._get_related_id(obj, 'questionnaire')
        )
        if questionnaire_id:
            questionnaire_data = self.context.get('questionnaires_data', {}).get(str(questionnaire_id))
            if questionnaire_data:
                return questionnaire_data.get('title', '')
        
        return ''

    def get_placa_vehiculo(self, obj) -> Optional[str]:
        """
        Retorna la placa del vehículo normalizada.
        Primero intenta desde el campo directo, luego deriva de respuestas.
        """
        # 1) Si está en la columna del modelo/entidad, normalízala
        placa_directa = self._get_field_value(obj, "placa_vehiculo")
        if placa_directa:
            normalized = _placa_or_none(placa_directa)
            if normalized:
                return normalized

        # 2) Derivar de respuestas si están disponibles en el contexto
        answers_data = self.context.get('answers_data', {}).get(str(self._get_field_value(obj, 'id')), [])
        
        # a) Primero, respuestas cuya pregunta tenga etiqueta 'placa'
        for answer_data in answers_data:
            question_data = answer_data.get('question', {})
            if question_data.get('semantic_tag') == 'placa' and answer_data.get('answer_text'):
                plate = _placa_or_none(answer_data['answer_text'])
                if plate:
                    return plate

        # b) Fallback: primera respuesta que normalice a placa
        for answer_data in answers_data:
            if answer_data.get('answer_text'):
                plate = _placa_or_none(answer_data['answer_text'])
                if plate:
                    return plate

        # 3) Fallback para modelos Django: consultar base de datos
        if hasattr(obj, '_state'):  # Es un modelo Django
            try:
                from app.infrastructure.models import Answer
                qs = (
                    Answer.objects
                    .filter(submission=obj, answer_text__isnull=False)
                    .select_related("question")
                    .order_by("-timestamp")[:50]
                )

                # a) Primero, respuestas cuya pregunta tenga etiqueta 'placa'
                for a in qs:
                    if a.question and getattr(a.question, "semantic_tag", None) == "placa":
                        plate = _placa_or_none(a.answer_text or "")
                        if plate:
                            return plate

                # b) Fallback: primera respuesta que normalice a placa
                for a in qs:
                    plate = _placa_or_none(a.answer_text or "")
                    if plate:
                        return plate
            except Exception:
                pass

        return None

    def get_contenedor(self, obj):
        """Retorna el número de contenedor."""
        return self._get_field_value(obj, 'contenedor')

    def get_precinto(self, obj):
        """Retorna el número de precinto."""
        return self._get_field_value(obj, 'precinto')

    def get_proveedor_id(self, obj):
        """Retorna el ID del proveedor."""
        return (
            self._get_field_value(obj, 'proveedor_id') or
            self._get_related_id(obj, 'proveedor')
        )

    def get_transportista_id(self, obj):
        """Retorna el ID del transportista."""
        return (
            self._get_field_value(obj, 'transportista_id') or
            self._get_related_id(obj, 'transportista')
        )

    def get_receptor_id(self, obj):
        """Retorna el ID del receptor."""
        return (
            self._get_field_value(obj, 'receptor_id') or
            self._get_related_id(obj, 'receptor')
        )

    def get_proveedor(self, obj):
        """Retorna los datos del proveedor."""
        proveedor = self._get_field_value(obj, 'proveedor')
        if proveedor:
            return ActorModelSerializer().to_representation(proveedor)
        return None

    def get_transportista(self, obj):
        """Retorna los datos del transportista."""
        transportista = self._get_field_value(obj, 'transportista')
        if transportista:
            return ActorModelSerializer().to_representation(transportista)
        return None

    def get_receptor(self, obj):
        """Retorna los datos del receptor."""
        receptor = self._get_field_value(obj, 'receptor')
        if receptor:
            return ActorModelSerializer().to_representation(receptor)
        return None

    def get_answers(self, obj):
        """Retorna las respuestas asociadas al submission."""
        # Intentar desde relación cargada (modelos Django)
        answers = self._get_field_value(obj, 'answers')
        if answers and hasattr(answers, 'all'):
            return AnswerReadSerializer(
                answers.all(), 
                many=True, 
                context=self.context
            ).data
        
        # Usar datos del contexto si están disponibles
        submission_id = self._get_field_value(obj, 'id')
        if submission_id:
            answers_data = self.context.get('answers_data', {}).get(str(submission_id), [])
            return AnswerReadSerializer(
                answers_data, 
                many=True, 
                context=self.context
            ).data
        
        return []





# ----------------------------------------------------------------------
# Slice Save & Advance (input/output)
# ----------------------------------------------------------------------
class SaveAndAdvanceInputSerializer(serializers.Serializer):
    """
    Serializer manual para el caso de uso Save and Advance.
    No depende de modelos Django y delega validaciones de dominio a servicios.
    """
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)

    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)

    # Soporte para múltiples archivos
    answer_file = serializers.FileField(required=False, allow_null=True)
    answer_file_extra = serializers.FileField(required=False, allow_null=True)

    # Soporte nativo para preguntas de actor
    actor_id = serializers.UUIDField(required=False, allow_null=True)

    force_truncate_future = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        """
        Valida estructura básica y delega validaciones de dominio a servicios.
        """
        # Normalizar texto vacío -> None
        txt = attrs.get("answer_text")
        if isinstance(txt, str):
            t = txt.strip()
            attrs["answer_text"] = t if t else None

        # Validar que los UUIDs sean válidos
        self._validate_uuid_field(attrs, "submission_id")
        self._validate_uuid_field(attrs, "question_id")
        
        if attrs.get("user_id"):
            self._validate_uuid_field(attrs, "user_id")
        
        if attrs.get("answer_choice_id"):
            self._validate_uuid_field(attrs, "answer_choice_id")
        
        if attrs.get("actor_id"):
            self._validate_uuid_field(attrs, "actor_id")

        # Validar archivos
        self._validate_files(attrs)

        # Las validaciones de dominio (como verificar que la pregunta existe,
        # que el actor es del tipo correcto, etc.) se delegan a los servicios
        # de aplicación que tienen acceso a los repositorios de dominio

        return attrs

    def _validate_uuid_field(self, attrs, field_name):
        """Valida que un campo UUID tenga formato válido."""
        value = attrs.get(field_name)
        if value:
            try:
                from uuid import UUID
                UUID(str(value))
            except (ValueError, TypeError):
                raise serializers.ValidationError({field_name: ["Formato de UUID inválido."]})

    def _validate_files(self, attrs):
        """Valida archivos de entrada."""
        files = []
        
        if attrs.get("answer_file"):
            files.append(attrs["answer_file"])
        
        if attrs.get("answer_file_extra"):
            files.append(attrs["answer_file_extra"])

        # Validar cada archivo
        for i, file_obj in enumerate(files):
            field_name = "answer_file" if i == 0 else "answer_file_extra"
            self._validate_single_file(file_obj, field_name)

    def _validate_single_file(self, file_obj, field_name):
        """Valida un archivo individual."""
        if not file_obj:
            return

        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        max_size = 10 * 1024 * 1024  # 10 MB
        
        content_type = getattr(file_obj, "content_type", None)
        if content_type not in allowed_types:
            raise serializers.ValidationError({
                field_name: ["Solo se permiten archivos JPG, PNG o PDF."]
            })
        
        if file_obj.size > max_size:
            raise serializers.ValidationError({
                field_name: ["El archivo no debe superar los 10MB."]
            })


class SaveAndAdvanceResponseSerializer(serializers.Serializer):
    """
    Serializer manual para respuesta de Save and Advance.
    Trabaja directamente con entidades de dominio y resultados de casos de uso.
    """
    saved_answer = serializers.SerializerMethodField()
    next_question_id = serializers.UUIDField(read_only=True, allow_null=True)
    next_question = serializers.SerializerMethodField()
    is_finished = serializers.BooleanField(read_only=True)
    derived_updates = serializers.JSONField(read_only=True)
    warnings = serializers.ListField(child=serializers.CharField(), read_only=True, allow_empty=True)

    def to_representation(self, instance):
        """
        Convierte el resultado del caso de uso a representación JSON.
        Maneja tanto dataclasses como diccionarios.
        """
        # Extraer datos del objeto resultado
        if hasattr(instance, '__dict__'):
            # Es un dataclass o objeto con atributos
            data = {
                'saved_answer': self.get_saved_answer(instance),
                'next_question_id': getattr(instance, 'next_question_id', None),
                'next_question': self.get_next_question(instance),
                'is_finished': getattr(instance, 'is_finished', False),
                'derived_updates': getattr(instance, 'derived_updates', {}),
                'warnings': getattr(instance, 'warnings', []),
            }
        else:
            # Es un diccionario
            data = {
                'saved_answer': self.get_saved_answer(instance),
                'next_question_id': instance.get('next_question_id'),
                'next_question': self.get_next_question(instance),
                'is_finished': instance.get('is_finished', False),
                'derived_updates': instance.get('derived_updates', {}),
                'warnings': instance.get('warnings', []),
            }

        return data

    def get_saved_answer(self, obj) -> Optional[Dict[str, Any]]:
        """Serializa la respuesta guardada."""
        # Extraer saved_answer del objeto
        saved = None
        if hasattr(obj, 'saved_answer'):
            saved = obj.saved_answer
        elif isinstance(obj, dict):
            saved = obj.get('saved_answer')
        
        if saved is None:
            return None

        # Usar el serializer de respuestas para convertir
        return AnswerReadSerializer(saved, context=self.context).to_representation(saved)

    def get_next_question(self, obj) -> Optional[Dict[str, Any]]:
        """Serializa la siguiente pregunta."""
        # Extraer next_question del objeto
        next_question = None
        if hasattr(obj, 'next_question'):
            next_question = obj.next_question
        elif isinstance(obj, dict):
            next_question = obj.get('next_question')
        
        if next_question is None:
            return None

        # Usar el serializer de preguntas para convertir
        return QuestionModelSerializer().to_representation(next_question)


class VerificationInputSerializer(serializers.Serializer):
    """
    Serializer manual para entrada de verificación OCR.
    No depende de modelos Django y valida estructura básica.
    """
    question_id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=["text", "document"], required=False, default="text")
    imagen = serializers.ImageField()

    def validate(self, attrs):
        """Valida estructura básica de la entrada."""
        # Validar UUID de la pregunta
        try:
            from uuid import UUID
            UUID(str(attrs["question_id"]))
        except (ValueError, TypeError):
            raise serializers.ValidationError({"question_id": ["Formato de UUID inválido."]})

        return attrs

    def validate_imagen(self, f):
        """Valida la imagen de entrada."""
        if not f:
            raise serializers.ValidationError("La imagen es obligatoria.")

        allowed_types = {"image/jpeg", "image/png"}
        max_size = 10 * 1024 * 1024  # 10 MB
        
        content_type = getattr(f, "content_type", "") or ""
        if content_type not in allowed_types:
            raise serializers.ValidationError("Solo se permiten imágenes JPG o PNG.")
        
        if f.size > max_size:
            raise serializers.ValidationError("La imagen no debe superar los 10MB.")
        
        return f


class VerificationResponseSerializer(serializers.Serializer):
    """
    Serializer manual para respuesta de verificación OCR.
    No depende de modelos Django y trabaja con datos puros.
    """
    ocr_raw = serializers.CharField(read_only=True)
    placa = serializers.CharField(read_only=True, allow_null=True)
    precinto = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    valido = serializers.BooleanField(read_only=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance):
        """
        Convierte el resultado de verificación a representación JSON.
        Maneja tanto diccionarios como objetos con atributos.
        """
        if isinstance(instance, dict):
            return {
                'ocr_raw': instance.get('ocr_raw', ''),
                'placa': instance.get('placa'),
                'precinto': instance.get('precinto'),
                'contenedor': instance.get('contenedor'),
                'valido': instance.get('valido', False),
                'semantic_tag': instance.get('semantic_tag'),
            }
        
        # Si es un objeto con atributos
        return {
            'ocr_raw': getattr(instance, 'ocr_raw', ''),
            'placa': getattr(instance, 'placa', None),
            'precinto': getattr(instance, 'precinto', None),
            'contenedor': getattr(instance, 'contenedor', None),
            'valido': getattr(instance, 'valido', False),
            'semantic_tag': getattr(instance, 'semantic_tag', None),
        }


class QuestionnaireListItemSerializer(serializers.Serializer):
    """
    Serializer manual para listado de cuestionarios.
    Trabaja directamente con entidades de dominio.
    """
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        """
        Convierte la entidad o modelo a representación JSON.
        """
        return {
            'id': self._get_field_value(instance, 'id'),
            'title': self._get_field_value(instance, 'title'),
            'version': self._get_field_value(instance, 'version'),
        }

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default


class HistorialItemSerializer(serializers.Serializer):
    """
    Serializer manual para items del historial.
    Trabaja directamente con entidades de dominio.
    """
    regulador_id = serializers.UUIDField(read_only=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    ultima_fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    fase1 = serializers.SerializerMethodField()
    fase2 = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """
        Convierte el item del historial a representación JSON.
        """
        # instance puede ser un dict o un objeto
        if isinstance(instance, dict):
            return {
                'regulador_id': instance.get('regulador_id'),
                'placa_vehiculo': instance.get('placa_vehiculo'),
                'contenedor': instance.get('contenedor'),
                'ultima_fecha_cierre': instance.get('ultima_fecha_cierre'),
                'fase1': self.get_fase1(instance),
                'fase2': self.get_fase2(instance),
            }
        else:
            return {
                'regulador_id': self._get_field_value(instance, 'regulador_id'),
                'placa_vehiculo': self._get_field_value(instance, 'placa_vehiculo'),
                'contenedor': self._get_field_value(instance, 'contenedor'),
                'ultima_fecha_cierre': self._get_field_value(instance, 'ultima_fecha_cierre'),
                'fase1': self.get_fase1(instance),
                'fase2': self.get_fase2(instance),
            }

    def get_fase1(self, obj):
        """Serializa la fase 1 del historial."""
        if isinstance(obj, dict):
            fase1 = obj.get('fase1')
        else:
            fase1 = self._get_field_value(obj, 'fase1')
        
        if fase1 is None:
            return None
        return SubmissionModelSerializer(context=self.context).to_representation(fase1)

    def get_fase2(self, obj):
        """Serializa la fase 2 del historial."""
        if isinstance(obj, dict):
            fase2 = obj.get('fase2')
        else:
            fase2 = self._get_field_value(obj, 'fase2')
        
        if fase2 is None:
            return None
        return SubmissionModelSerializer(context=self.context).to_representation(fase2)

    def _get_field_value(self, obj, field_name, default=None):
        """Extrae valor de campo de manera segura."""
        try:
            return getattr(obj, field_name, default)
        except Exception:
            return default
