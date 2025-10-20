"""
Serializadores manuales (DRF) que trabajan con ENTIDADES de dominio.
Ubicación: interfaces/ (presentación). No dependen de modelos Django ni del ORM.
"""

from __future__ import annotations

from typing import Optional, Any, Dict, List
from uuid import UUID
from rest_framework import serializers

# Importa tus entidades de dominio (dataclasses), no modelos.
from app.domain.entities import Submission, Answer, Question, Choice, Questionnaire


# =============================================================================
# Helpers internos (no dominio)
# =============================================================================

def _get(obj: Any, name: str, default=None):
    """getattr seguro para entidades de dominio con cambios de nombres."""
    try:
        return getattr(obj, name)
    except Exception:
        return default

def _first_non_null(*values):
    for v in values:
        if v is not None:
            return v
    return None


# =============================================================================
# READ SERIALIZERS (Domain -> JSON)
# =============================================================================

class DomainChoiceReadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    branch_to = serializers.UUIDField(read_only=True, allow_null=True)

    def to_representation(self, instance: Choice) -> Dict[str, Any]:
        return {
            "id": _get(instance, "id"),
            "text": _get(instance, "text") or "",
            "branch_to": _get(instance, "branch_to"),
        }


class DomainQuestionReadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    choices = DomainChoiceReadSerializer(many=True, read_only=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)
    file_mode = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance: Question) -> Dict[str, Any]:
        choices = _get(instance, "choices") or []
        return {
            "id": _get(instance, "id"),
            "text": _get(instance, "text") or "",
            "type": _get(instance, "type") or "text",
            "required": bool(_get(instance, "required", False)),
            "order": int(_get(instance, "order", 0)),
            "choices": [DomainChoiceReadSerializer().to_representation(c) for c in choices],
            "semantic_tag": _get(instance, "semantic_tag"),
            "file_mode": _get(instance, "file_mode"),
        }


class DomainQuestionnaireReadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    timezone = serializers.CharField(read_only=True)
    questions = DomainQuestionReadSerializer(many=True, read_only=True)

    def to_representation(self, instance: Questionnaire) -> Dict[str, Any]:
        qs = _get(instance, "questions") or []
        return {
            "id": _get(instance, "id"),
            "title": _get(instance, "title") or "",
            "version": _get(instance, "version") or "",
            "timezone": _get(instance, "timezone") or "America/Bogota",
            "questions": [DomainQuestionReadSerializer().to_representation(q) for q in qs],
        }


class DomainAnswerReadSerializer(serializers.Serializer):
    """
    Representación tolerante a cambios:
    - timestamp/created_at/updated_at
    - answer_file_path/upload
    - meta y (si existe) ocr_meta
    - campos tabulares (si existen): is_tabular, table_id, row_index
    """
    id = serializers.UUIDField(read_only=True)
    submission_id = serializers.UUIDField(read_only=True)
    question_id = serializers.UUIDField(read_only=True)

    # Campos “clásicos”
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_text = serializers.CharField(read_only=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(read_only=True, allow_null=True)

    # Archivo (ruta o upload) y metadata
    answer_file_path = serializers.CharField(read_only=True, allow_null=True)
    meta = serializers.JSONField(read_only=True)
    ocr_meta = serializers.JSONField(read_only=True)

    # Fechas
    timestamp = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, allow_null=True)
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)

    # Tabular (si aplica)
    is_tabular = serializers.BooleanField(read_only=True, default=False)
    table_id = serializers.UUIDField(read_only=True, allow_null=True)
    row_index = serializers.IntegerField(read_only=True, allow_null=True)

    # Enriquecidos para frontend
    answer_file = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    answer_choice = serializers.SerializerMethodField()

    def to_representation(self, instance: Answer) -> Dict[str, Any]:
        # Compat fechas
        ts = _first_non_null(_get(instance, "timestamp"), _get(instance, "created_at"))
        data = {
            "id": _get(instance, "id"),
            "submission_id": _get(instance, "submission_id"),
            "question_id": _get(instance, "question_id"),

            "user_id": _get(instance, "user_id"),  # podría no existir en tu nueva entidad
            "answer_text": _get(instance, "answer_text"),
            "answer_choice_id": _get(instance, "answer_choice_id"),

            # Compat archivo (upload/answer_file_path)
            "answer_file_path": _first_non_null(_get(instance, "answer_file_path"), _get(instance, "upload")),

            "meta": _get(instance, "meta") or {},
            "ocr_meta": _get(instance, "ocr_meta") or {},

            "timestamp": ts,
            "created_at": _get(instance, "created_at"),
            "updated_at": _get(instance, "updated_at"),

            "is_tabular": bool(_get(instance, "is_tabular", False)),
            "table_id": _get(instance, "table_id"),
            "row_index": _get(instance, "row_index"),
        }

        # Enriquecidos
        data["answer_file"] = self.get_answer_file(instance)
        data["question"] = self.get_question(instance)
        data["answer_choice"] = self.get_answer_choice(instance)
        return data

    def get_answer_file(self, obj: Answer) -> Optional[str]:
        path = _first_non_null(_get(obj, "answer_file_path"), _get(obj, "upload"))
        if not path:
            return None
        # Si tienes un servicio de storage, úsalo aquí. Por ahora, una URL relativa estable:
        return f"/api/media/{path}".replace("//", "/")

    def get_question(self, obj: Answer) -> Optional[Dict[str, Any]]:
        qdata = (self.context.get("questions_data") or {}).get(str(_get(obj, "question_id")))
        if not qdata:
            return {"id": str(_get(obj, "question_id")), "text": "", "type": "", "semantic_tag": None}
        return {
            "id": str(_get(obj, "question_id")),
            "text": qdata.get("text", ""),
            "type": qdata.get("type", ""),
            "semantic_tag": qdata.get("semantic_tag"),
        }

    def get_answer_choice(self, obj: Answer) -> Optional[Dict[str, Any]]:
        cid = _get(obj, "answer_choice_id")
        if not cid:
            return None
        cdata = (self.context.get("choices_data") or {}).get(str(cid))
        if not cdata:
            return {"id": str(cid), "text": ""}
        return {"id": str(cid), "text": cdata.get("text", "")}


class DomainSubmissionReadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    questionnaire_id = serializers.UUIDField(read_only=True)
    tipo_fase = serializers.CharField(read_only=True)
    regulador_id = serializers.UUIDField(read_only=True, allow_null=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    finalizado = serializers.BooleanField(read_only=True)

    # Compat fechas
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)

    # Enriquecidos
    questionnaire_title = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    def to_representation(self, instance: Submission) -> Dict[str, Any]:
        return {
            "id": _get(instance, "id"),
            "questionnaire_id": _get(instance, "questionnaire_id"),
            "questionnaire": _get(instance, "questionnaire_id"),  # compat frontend
            "tipo_fase": _get(instance, "tipo_fase"),
            "regulador_id": _get(instance, "regulador_id"),
            "placa_vehiculo": _get(instance, "placa_vehiculo"),
            "finalizado": bool(_get(instance, "finalizado", False)),
            "fecha_creacion": _first_non_null(_get(instance, "fecha_creacion"), _get(instance, "created_at")),
            "fecha_cierre": _first_non_null(_get(instance, "fecha_cierre"), _get(instance, "closed_at")),
            "questionnaire_title": self.get_questionnaire_title(instance),
            "answers": self.get_answers(instance),
        }

    def get_questionnaire_title(self, obj: Submission) -> str:
        q = (self.context.get("questionnaires_data") or {}).get(str(_get(obj, "questionnaire_id")))
        return (q or {}).get("title", "")

    def get_answers(self, obj: Submission) -> List[Dict[str, Any]]:
        answers = (self.context.get("answers_data") or {}).get(str(_get(obj, "id")), [])
        return [DomainAnswerReadSerializer(context=self.context).to_representation(a) for a in answers]


# =============================================================================
# USE-CASE RESPONSE SERIALIZERS
# =============================================================================

class DomainQuestionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    choices = DomainChoiceReadSerializer(many=True, read_only=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)
    file_mode = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance: Question) -> Dict[str, Any]:
        return DomainQuestionReadSerializer().to_representation(instance)


class SaveAndAdvanceEntityResponseSerializer(serializers.Serializer):
    saved_answer = serializers.SerializerMethodField()
    next_question_id = serializers.UUIDField(allow_null=True, read_only=True)
    next_question = serializers.SerializerMethodField()
    is_finished = serializers.BooleanField(read_only=True)
    derived_updates = serializers.JSONField(read_only=True)
    warnings = serializers.ListField(child=serializers.CharField(), read_only=True)

    def get_saved_answer(self, obj) -> Optional[Dict[str, Any]]:
        saved = getattr(obj, "saved_answer", None)
        if saved is None:
            return None
        return DomainAnswerReadSerializer(context=self.context).to_representation(saved)

    def get_next_question(self, obj) -> Optional[Dict[str, Any]]:
        nxt = getattr(obj, "next_question", None)
        if nxt is None:
            return None
        return DomainQuestionDetailSerializer().to_representation(nxt)


class VerificationEntityResponseSerializer(serializers.Serializer):
    ocr_raw = serializers.CharField(read_only=True)
    placa = serializers.CharField(read_only=True, allow_null=True)
    precinto = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    valido = serializers.BooleanField(read_only=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ocr_raw": instance.get("ocr_raw", ""),
            "placa": instance.get("placa"),
            "precinto": instance.get("precinto"),
            "contenedor": instance.get("contenedor"),
            "valido": bool(instance.get("valido", False)),
            "semantic_tag": instance.get("semantic_tag"),
        }


class QuestionnaireListEntitySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)

    def to_representation(self, instance: Questionnaire) -> Dict[str, Any]:
        return {"id": _get(instance, "id"), "title": _get(instance, "title") or "", "version": _get(instance, "version") or ""}


# =============================================================================
# COMMAND INPUT SERIALIZERS (JSON -> Application Command)
# =============================================================================

class CreateSubmissionCommandSerializer(serializers.Serializer):
    questionnaire_id = serializers.UUIDField()
    tipo_fase = serializers.ChoiceField(choices=["entrada", "salida"])
    regulador_id = serializers.UUIDField(required=False, allow_null=True)
    placa_vehiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        placa = attrs.get("placa_vehiculo")
        if placa:
            placa = str(placa).strip()
            attrs["placa_vehiculo"] = placa if placa else None
        else:
            attrs["placa_vehiculo"] = None
        return attrs

    def to_command(self):
        from app.application.commands import CreateSubmissionCommand
        return CreateSubmissionCommand(**self.validated_data)


class SaveAnswerCommandSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()

    # Soporta texto/choice/archivo
    user_id = serializers.UUIDField(required=False, allow_null=True)
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file_path = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Meta
    ocr_meta = serializers.DictField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, allow_null=True)

    # Campos tabulares (si aplica)
    table_id = serializers.UUIDField(required=False, allow_null=True)
    row_index = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        # Normaliza texto
        text = attrs.get("answer_text")
        if text is not None:
            text = str(text).strip()
            attrs["answer_text"] = text if text else None

        has_text = bool(attrs.get("answer_text"))
        has_choice = attrs.get("answer_choice_id") is not None
        has_file = bool(attrs.get("answer_file_path"))

        if not (has_text or has_choice or has_file):
            raise serializers.ValidationError({"non_field_errors": ["Debes enviar al menos uno de: answer_text, answer_choice_id o answer_file_path."]})

        # row_index si viene debe ser >= 0
        if attrs.get("row_index") is not None and attrs["row_index"] < 0:
            raise serializers.ValidationError({"row_index": ["Debe ser >= 0."]})

        return attrs

    def to_command(self):
        from app.application.commands import SaveAnswerCommand
        return SaveAnswerCommand(**self.validated_data)


# =============================================================================
# RESPUESTAS AGREGADAS / HISTORIAL / LISTADOS
# =============================================================================

class DomainSubmissionListSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    questionnaire_id = serializers.UUIDField(read_only=True)
    questionnaire_title = serializers.SerializerMethodField()
    tipo_fase = serializers.CharField(read_only=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    finalizado = serializers.BooleanField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)

    def to_representation(self, instance: Submission) -> Dict[str, Any]:
        return {
            "id": _get(instance, "id"),
            "questionnaire_id": _get(instance, "questionnaire_id"),
            "questionnaire": _get(instance, "questionnaire_id"),
            "questionnaire_title": self.get_questionnaire_title(instance),
            "tipo_fase": _get(instance, "tipo_fase"),
            "placa_vehiculo": _get(instance, "placa_vehiculo"),
            "finalizado": bool(_get(instance, "finalizado", False)),
            "fecha_creacion": _first_non_null(_get(instance, "fecha_creacion"), _get(instance, "created_at")),
            "fecha_cierre": _first_non_null(_get(instance, "fecha_cierre"), _get(instance, "closed_at")),
        }

    def get_questionnaire_title(self, obj: Submission) -> str:
        q = (self.context.get("questionnaires_data") or {}).get(str(_get(obj, "questionnaire_id")))
        return (q or {}).get("title", "")


class EntityBasedSubmissionDetailSerializer(serializers.Serializer):
    submission = DomainSubmissionReadSerializer()
    answers = DomainAnswerReadSerializer(many=True)
    questionnaire = DomainQuestionnaireReadSerializer()

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "submission": DomainSubmissionReadSerializer(context=self.context).to_representation(instance.get("submission")),
            "answers": [DomainAnswerReadSerializer(context=self.context).to_representation(a) for a in (instance.get("answers") or [])],
            "questionnaire": DomainQuestionnaireReadSerializer().to_representation(instance.get("questionnaire")) if instance.get("questionnaire") else None,
        }


class EntityBasedHistoryItemSerializer(serializers.Serializer):
    regulador_id = serializers.UUIDField(read_only=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    ultima_fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    fase1 = DomainSubmissionReadSerializer(read_only=True, allow_null=True)
    fase2 = DomainSubmissionReadSerializer(read_only=True, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "regulador_id": instance.get("regulador_id"),
            "placa_vehiculo": instance.get("placa_vehiculo"),
            "contenedor": instance.get("contenedor"),
            "ultima_fecha_cierre": instance.get("ultima_fecha_cierre"),
            "fase1": DomainSubmissionReadSerializer(context=self.context).to_representation(instance.get("fase1")) if instance.get("fase1") else None,
            "fase2": DomainSubmissionReadSerializer(context=self.context).to_representation(instance.get("fase2")) if instance.get("fase2") else None,
        }


class EntityBasedQuestionDetailResponseSerializer(serializers.Serializer):
    question = DomainQuestionDetailSerializer()

    def to_representation(self, instance) -> Dict[str, Any]:
        return DomainQuestionDetailSerializer().to_representation(instance)


class EntityBasedSubmissionListResponseSerializer(serializers.Serializer):
    results = DomainSubmissionListSerializer(many=True)
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "results": [DomainSubmissionListSerializer(context=self.context).to_representation(s) for s in (instance.get("results") or [])],
            "count": int(instance.get("count", 0)),
            "next": instance.get("next"),
            "previous": instance.get("previous"),
        }
