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
    Entrada para guardar una respuesta de usuario.
    Permite texto, opción, archivo(s). Además, soporta:
      - actor_id: cuando la pregunta tiene semantic_tag proveedor/transportista/receptor
      - ocr_meta/meta: para adjuntar metadatos (OCR, snapshot, etc.)
    """
    question_id = serializers.UUIDField()
    submission_id = serializers.UUIDField()

    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    # se mantiene (una sola). Para múltiples, la vista lee request.FILES.getlist(...)
    answer_file = serializers.FileField(required=False, allow_null=True)

    # NUEVO: cuando la respuesta referencia un catálogo maestro
    actor_id = serializers.UUIDField(required=False, allow_null=True)

    # NUEVO: metadatos opcionales
    ocr_meta = serializers.DictField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, allow_null=True)

    def validate(self, attrs):
        """
        Valida que venga al menos: texto, opción, archivo(s) o actor_id.
        También considera archivos múltiples en request.FILES.
        Valida que:
          - question_id exista;
          - si viene answer_choice_id, pertenezca a esa pregunta;
          - si semantic_tag es proveedor/transportista/receptor, se exija actor_id y el tipo coincida.
        """
        req = self.context.get("request")

        files = []
        if req:
            files = req.FILES.getlist("answer_file") or req.FILES.getlist("answer_files")

        has_payload = bool(
            (attrs.get("answer_text") or "").strip()
            or attrs.get("answer_choice_id")
            or attrs.get("answer_file")
            or files
            or attrs.get("actor_id")
        )
        if not has_payload:
            raise serializers.ValidationError(
                {"non_field_errors": ["Debes enviar una respuesta (texto, opción, archivo(s) o actor)."]}
            )

        # 1) Validar pregunta / opciones
        try:
            question = Question.objects.get(id=attrs["question_id"])
        except Question.DoesNotExist:
            raise serializers.ValidationError({"question_id": ["Pregunta no encontrada."]})

        choice_id = attrs.get("answer_choice_id")
        if choice_id:
            try:
                choice = Choice.objects.get(id=choice_id)
            except Choice.DoesNotExist:
                raise serializers.ValidationError({"answer_choice_id": ["Opción no encontrada."]})
            if choice.question_id != question.id:
                raise serializers.ValidationError(
                    {"answer_choice_id": ["La opción no pertenece a la pregunta indicada."]}
                )

        # 2) Validación específica para actor (si aplica)
        actor_id = attrs.get("actor_id")
        if (getattr(question, "semantic_tag", "") or "").lower() in ("proveedor", "transportista", "receptor"):
            if not actor_id:
                raise serializers.ValidationError(
                    {"actor_id": [f"Debes enviar actor_id para la pregunta '{question.semantic_tag}'."]}
                )
            try:
                actor = Actor.objects.get(id=actor_id)
            except Actor.DoesNotExist:
                raise serializers.ValidationError({"actor_id": ["Actor no encontrado."]})

            expected = {
                "proveedor": Actor.Tipo.PROVEEDOR,
                "transportista": Actor.Tipo.TRANSPORTISTA,
                "receptor": Actor.Tipo.RECEPTOR,
            }[question.semantic_tag]

            if actor.tipo != expected:
                raise serializers.ValidationError(
                    {"actor_id": [f"El actor debe ser de tipo {expected}."]}
                )

            # Guardar objeto para capa superior (vista/servicio)
            attrs["_actor_obj"] = actor

        # 5) Adjuntar Question para capa superior (evita doble búsqueda)
        attrs["_question_obj"] = question

        # Normalizar texto vacío -> None
        txt = attrs.get("answer_text")
        if isinstance(txt, str):
            txt = txt.strip()
            attrs["answer_text"] = txt if txt else None

        return attrs

    def validate_answer_file(self, value):
        allowed = {"image/jpeg", "image/png", "application/pdf"}
        max_size = 10 * 1024 * 1024  # 10 MB
        if value:
            if getattr(value, "content_type", None) not in allowed:
                raise serializers.ValidationError("Solo se permiten archivos JPG, PNG o PDF.")
            if value.size > max_size:
                raise serializers.ValidationError("El archivo no debe superar los 10MB.")
        return value


# ----------------------------------------------------------------------
# READ – manuales sobre modelos
# ----------------------------------------------------------------------
class ActorModelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tipo = serializers.CharField()
    nombre = serializers.CharField()
    documento = serializers.CharField(allow_null=True)
    activo = serializers.BooleanField()


class ChoiceModelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    branch_to = serializers.SerializerMethodField()

    def get_branch_to(self, obj):
        bt = getattr(obj, "branch_to_id", None) or (getattr(obj, "branch_to", None).id if getattr(obj, "branch_to", None) else None)
        return str(bt) if bt else None


class QuestionModelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    type = serializers.CharField()
    required = serializers.BooleanField()
    order = serializers.IntegerField()
    choices = ChoiceModelSerializer(many=True, required=False)
    file_mode = serializers.CharField(required=False)
    semantic_tag = serializers.CharField(required=False)


class QuestionnaireModelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    version = serializers.CharField()
    timezone = serializers.CharField()
    questions = QuestionModelSerializer(many=True, required=False)


class AnswerReadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)

    # Estructura enriquecida esperada por el front
    question = serializers.SerializerMethodField()
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice = serializers.SerializerMethodField()
    answer_file = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField()

    # Campos aplanados útiles para la UI/búsqueda
    question_id = serializers.ReadOnlyField(source="question.id")
    question_text = serializers.ReadOnlyField(source="question.text")
    question_type = serializers.ReadOnlyField(source="question.type")
    question_tag = serializers.ReadOnlyField(source="question.semantic_tag")
    answer_choice_id = serializers.ReadOnlyField(source="answer_choice.id")

    # ---- helpers de acceso seguro ----
    def _get_attr(self, obj, name, default=None):
        try:
            return getattr(obj, name, default)
        except Exception:
            return default

    def get_question(self, obj):
        q = self._get_attr(obj, "question")
        if not q:
            return None
        # Compatibilidad: algunos modelos usan "label"
        text = getattr(q, "text", None) or getattr(q, "label", None)
        return {
            "id": str(getattr(q, "id")),
            "text": text,
            "type": getattr(q, "type", None),
            "semantic_tag": getattr(q, "semantic_tag", None),
        }

    def get_answer_choice(self, obj):
        c = self._get_attr(obj, "answer_choice")
        if not c:
            return None
        # 🔧 FIX: el front espera "text" (no "label")
        text = getattr(c, "text", None) or getattr(c, "label", None) or getattr(c, "name", None)
        return {"id": str(getattr(c, "id")), "text": text}

    def get_answer_file(self, obj):
        f = self._get_attr(obj, "answer_file")
        if not f:
            return None
        # genera URL segura con autenticación (como ya venías haciendo)
        try:
            from app.infrastructure.storage import get_secure_media_url
            return get_secure_media_url(f.path)
        except Exception:
            return None


# ----------------------------------------------------------------------
# WRITE – básicos (no OCR)
# ----------------------------------------------------------------------
class AnswerWriteSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)

    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file = serializers.FileField(required=False, allow_null=True)

    ocr_meta = serializers.JSONField(required=False, read_only=True)
    meta = serializers.JSONField(required=False, read_only=True)

    def validate(self, attrs):
        text = (attrs.get("answer_text") or "").strip()
        has_text = bool(text)
        has_choice = attrs.get("answer_choice_id") is not None
        has_file = attrs.get("answer_file") is not None

        if not (has_text or has_choice or has_file):
            raise serializers.ValidationError(
                "Debes enviar al menos uno de: answer_text, answer_choice_id o answer_file."
            )

        attrs["answer_text"] = text if has_text else None
        return attrs

class SubmissionCreateSerializer(serializers.Serializer):
    questionnaire = serializers.UUIDField(source="questionnaire_id")
    tipo_fase = serializers.ChoiceField(choices=["entrada", "salida"])
    regulador_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    placa_vehiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)

    def validate(self, data):
        if not data.get("questionnaire_id"):
            raise serializers.ValidationError({"questionnaire": "Este campo es obligatorio."})
        return data

# ----------------------------------------------------------------------
# Submission (modelo) con respuestas embebidas (READ)
# ----------------------------------------------------------------------
class SubmissionModelSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    questionnaire = serializers.UUIDField(source="questionnaire_id")
    questionnaire_title = serializers.CharField(source="questionnaire.title")
    tipo_fase = serializers.CharField()
    placa_vehiculo = serializers.SerializerMethodField()

    regulador_id = serializers.UUIDField(allow_null=True)
    fecha_creacion = serializers.DateTimeField()
    finalizado = serializers.BooleanField()
    fecha_cierre = serializers.DateTimeField(allow_null=True)
    contenedor = serializers.CharField(allow_null=True)
    precinto = serializers.CharField(allow_null=True)

    proveedor_id = serializers.UUIDField(source="proveedor.id", allow_null=True)
    transportista_id = serializers.UUIDField(source="transportista.id", allow_null=True)
    receptor_id = serializers.UUIDField(source="receptor.id", allow_null=True)

    proveedor = ActorModelSerializer(allow_null=True)
    transportista = ActorModelSerializer(allow_null=True)
    receptor = ActorModelSerializer(allow_null=True)

    # detalle
    answers = AnswerReadSerializer(many=True)

    class Meta:
        fields = [
            "id",
            "questionnaire",
            "questionnaire_title",
            "tipo_fase",
            "placa_vehiculo",
            "regulador_id",
            "fecha_creacion",
            "finalizado",
            "fecha_cierre",
            "contenedor",
            "precinto",
            # catálogos
            "proveedor_id",
            "transportista_id",
            "receptor_id",
            "proveedor",
            "transportista",
            "receptor",
            # detalle
            "answers",
        ]

    def get_placa_vehiculo(self, obj) -> Optional[str]:
        # 1) Si está en la columna del modelo, normalízala; si no es válida,
        # deja None.
        if getattr(obj, "placa_vehiculo", None):
            return _placa_or_none(obj.placa_vehiculo)

        # 2) Derivar de respuestas priorizando semantic_tag == "placa"
        qs = (
            Answer.objects
            .filter(submission=obj, answer_text__isnull=False)
            .select_related("question")
            .order_by("-timestamp")[:50]
        )

        # a) primero, respuestas cuya pregunta tenga etiqueta 'placa'
        for a in qs:
            if a.question and getattr(a.question, "semantic_tag", None) == "placa":
                plate = _placa_or_none(a.answer_text or "")
                if plate:
                    return plate

        # b) fallback: primera respuesta que normalice a placa
        for a in qs:
            plate = _placa_or_none(a.answer_text or "")
            if plate:
                return plate

        return None


# ----------------------------------------------------------------------
# Serializers para ENTIDADES del dominio (admin)
# ----------------------------------------------------------------------
class DomainChoiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    branch_to = serializers.UUIDField(allow_null=True, required=False)


class DomainQuestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    type = serializers.CharField()
    required = serializers.BooleanField()
    order = serializers.IntegerField()
    choices = DomainChoiceSerializer(many=True, required=False, allow_null=True)
    semantic_tag = serializers.CharField(required=False, allow_null=True)
    file_mode = serializers.CharField(required=False, allow_null=True)


class DomainQuestionnaireSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    version = serializers.CharField()
    timezone = serializers.CharField()
    questions = DomainQuestionSerializer(many=True)


# ----------------------------------------------------------------------
# Slice Save & Advance (input/output)
# ----------------------------------------------------------------------
class SaveAndAdvanceInputSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)

    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)

    # Aceptamos 0..2 archivos (no OCR) o exactamente 1 (OCR). La cardinalidad real la valida el servicio.
    answer_file = serializers.FileField(required=False, allow_null=True)
    answer_file_extra = serializers.FileField(required=False, allow_null=True)

    # NUEVO: Soporte nativo a preguntas de actor
    actor_id = serializers.UUIDField(required=False, allow_null=True)

    force_truncate_future = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        # Normaliza string vacío -> None (evita confusión en servicio)
        txt = attrs.get("answer_text")
        if isinstance(txt, str):
            t = txt.strip()
            attrs["answer_text"] = t if t else None

        # Si es pregunta de actor, exigir actor_id (o compat: answer_choice_id)
        try:
            q = Question.objects.get(id=attrs["question_id"])
        except Question.DoesNotExist:
            raise serializers.ValidationError({"question_id": ["Pregunta no encontrada."]})

        from app.domain import rules as _rules
        tag = _rules.canonical_semantic_tag(getattr(q, "semantic_tag", ""))

        if tag in {"proveedor", "transportista", "receptor"}:
            actor_id = attrs.get("actor_id") or attrs.get("answer_choice_id")
            if not actor_id:
                raise serializers.ValidationError({"actor_id": [f"Debes enviar actor_id para la pregunta '{tag}'."]})
            try:
                actor = Actor.objects.get(id=actor_id)
            except Actor.DoesNotExist:
                raise serializers.ValidationError({"actor_id": ["Actor no encontrado."]})

            expected = {
                "proveedor": Actor.Tipo.PROVEEDOR,
                "transportista": Actor.Tipo.TRANSPORTISTA,
                "receptor": Actor.Tipo.RECEPTOR,
            }[tag]
            if actor.tipo != expected:
                raise serializers.ValidationError({"actor_id": [f"El actor debe ser de tipo {expected}."]})

            # Guardar objeto y campo destino para que la vista orqueste la FK sin reglas de negocio
            attrs["_actor_obj"] = actor
            attrs["_actor_field"] = f"{tag}_id"

            # Evita confundir al caso de uso con una Choice inexistente
            attrs["answer_choice_id"] = None

            # Si no vino texto, guarda el nombre del actor para auditoría
            if not attrs.get("answer_text"):
                attrs["answer_text"] = actor.nombre

        return attrs


class SaveAndAdvanceResponseSerializer(serializers.Serializer):
    saved_answer = serializers.SerializerMethodField()
    next_question_id = serializers.UUIDField(allow_null=True)
    next_question = QuestionModelSerializer(allow_null=True, required=False)
    is_finished = serializers.BooleanField()
    derived_updates = serializers.JSONField()
    warnings = serializers.ListField(child=serializers.CharField(), allow_empty=True)

    def get_saved_answer(self, obj) -> Any:
        # obj es un SaveAndAdvanceResult (dataclass), no un dict
        request = self.context.get("request")
        saved = getattr(obj, "saved_answer", None)
        if saved is None:
            # por compatibilidad, intenta dict si alguien envía un dict en tests
            try:
                saved = obj["saved_answer"]  # type: ignore[index]
            except Exception:
                return None
        return AnswerReadSerializer(saved, context={"request": request}).data


class VerificationInputSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=["text", "document"], required=False, default="text")
    imagen = serializers.ImageField()

    def validate_imagen(self, f):
        allowed = {"image/jpeg", "image/png"}
        max_size = 10 * 1024 * 1024  # 10 MB
        ctype = getattr(f, "content_type", "") or ""
        if ctype not in allowed:
            raise serializers.ValidationError("Solo se permiten imágenes JPG o PNG.")
        if f.size > max_size:
            raise serializers.ValidationError("La imagen no debe superar los 10MB.")
        return f


class VerificationResponseSerializer(serializers.Serializer):
    ocr_raw = serializers.CharField()
    # Campos opcionales según el semantic_tag de la pregunta
    placa = serializers.CharField(required=False, allow_null=True)
    precinto = serializers.CharField(required=False, allow_null=True)
    contenedor = serializers.CharField(required=False, allow_null=True)
    valido = serializers.BooleanField()


class QuestionnaireListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    version = serializers.CharField()


class HistorialItemSerializer(serializers.Serializer):
    regulador_id = serializers.UUIDField()
    placa_vehiculo = serializers.CharField(allow_null=True, required=False)
    contenedor = serializers.CharField(allow_null=True, required=False)
    ultima_fecha_cierre = serializers.DateTimeField(allow_null=True)

    # Embebemos las submissions usando el serializer de modelo
    fase1 = SubmissionModelSerializer(allow_null=True)
    fase2 = SubmissionModelSerializer(allow_null=True)
