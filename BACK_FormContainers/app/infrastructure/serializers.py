# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from rest_framework import serializers

from app.domain.rules import normalizar_placa as _norm_placa

# Sentinela de módulo para evitar problemas de alcance en validate()
_UNSET = object()


# ========= Helpers comunes =========
class SafeGetMixin:
    def _get(self, obj, name, default=None):
        try:
            return getattr(obj, name)
        except Exception:
            return default

    def _rel_id(self, obj, rel):
        try:
            o = getattr(obj, rel, None)
            return getattr(o, "id", None) if o else None
        except Exception:
            return None


def _validate_file(file_obj, *, field="file", types=None, max_mb=10):
    if not file_obj:
        return
    types = types or {"image/jpeg", "image/png", "application/pdf"}
    if getattr(file_obj, "content_type", None) not in types:
        raise serializers.ValidationError({field: ["Tipo de archivo no permitido."]})
    if file_obj.size > max_mb * 1024 * 1024:
        raise serializers.ValidationError({field: [f"Máximo {max_mb}MB."]})


# ========= INPUT: Guardar respuesta básica =========
class GuardarRespuestaSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file = serializers.FileField(required=False, allow_null=True)
    actor_id = serializers.UUIDField(required=False, allow_null=True)
    ocr_meta = serializers.DictField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, allow_null=True)

    def validate(self, attrs):
        txt = (attrs.get("answer_text") or "").strip()
        attrs["answer_text"] = txt or None
        if not any([attrs.get("answer_text"), attrs.get("answer_choice_id"),
                    attrs.get("answer_file"), attrs.get("actor_id")]):
            raise serializers.ValidationError({"answer": ["Debes enviar texto, opción, archivo(s) o actor."]})
        _validate_file(attrs.get("answer_file"), field="answer_file")
        if attrs.get("ocr_meta") and not isinstance(attrs["ocr_meta"], dict):
            raise serializers.ValidationError({"ocr_meta": ["Debe ser dict."]})
        if attrs.get("meta") and not isinstance(attrs["meta"], dict):
            raise serializers.ValidationError({"meta": ["Debe ser dict."]})
        return attrs


# ========= READ: Choice / Question / Questionnaire mínimos =========
class ChoiceModelSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    branch_to = serializers.SerializerMethodField()

    def get_branch_to(self, obj):
        return getattr(obj, "branch_to_id", None) or getattr(getattr(obj, "branch_to", None), "id", None)


class QuestionModelSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    text = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    file_mode = serializers.CharField(read_only=True, allow_null=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)
    choices = serializers.SerializerMethodField()

    def get_choices(self, obj):
        qs = getattr(obj, "choices", None)
        if hasattr(qs, "all"):
            qs = qs.all()
        if not qs:
            return []
        return ChoiceModelSerializer(qs, many=True).data


class QuestionnaireModelSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    timezone = serializers.CharField(read_only=True)
    questions = serializers.SerializerMethodField()

    def get_questions(self, obj):
        qs = getattr(obj, "questions", None)
        if hasattr(qs, "all"):
            qs = qs.all()
        if not qs:
            return []
        return QuestionModelSerializer(qs, many=True).data


# ========= READ: Answer (ligero, con enriquecidos mínimos) =========
class AnswerReadSerializer(SafeGetMixin, serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    submission_id = serializers.UUIDField(read_only=True)
    question_id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_text = serializers.CharField(read_only=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(read_only=True, allow_null=True)
    answer_file_path = serializers.CharField(read_only=True, allow_null=True)
    timestamp = serializers.DateTimeField(read_only=True)

    question = serializers.SerializerMethodField()
    answer_choice = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()
    ocr_meta = serializers.SerializerMethodField()

    def to_representation(self, inst):
        data = super().to_representation(inst)
        if not data.get("answer_file_path"):
            f = self._get(inst, "answer_file")
            data["answer_file_path"] = getattr(f, "name", None) if f else None
        return data

    def get_question(self, obj):
        q = self._get(obj, "question")
        if q:
            return {"id": str(getattr(q, "id", None)), "text": getattr(q, "text", ""),
                    "type": getattr(q, "type", ""), "semantic_tag": getattr(q, "semantic_tag", None)}
        qid = self._get(obj, "question_id")
        m = self.context.get("questions_data", {}).get(str(qid), {}) if qid else {}
        return {"id": str(qid) if qid else None, "text": m.get("text", ""), "type": m.get("type", ""),
                "semantic_tag": m.get("semantic_tag")}

    def get_answer_choice(self, obj):
        c = self._get(obj, "answer_choice")
        if c:
            return {"id": str(getattr(c, "id", None)), "text": getattr(c, "text", "")}
        cid = self._get(obj, "answer_choice_id")
        if not cid:
            return None
        m = self.context.get("choices_data", {}).get(str(cid), {})
        return {"id": str(cid), "text": m.get("text", "")}

    def get_meta(self, obj):
        m = self._get(obj, "meta") or {}
        return m if isinstance(m, dict) else {}

    def get_ocr_meta(self, obj):
        m = self.get_meta(obj)
        om = m.get("ocr_meta")
        return om if isinstance(om, dict) else None


# ========= WRITE: Answer (sencillo) =========
class AnswerWriteSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file = serializers.FileField(required=False, allow_null=True)
    ocr_meta = serializers.JSONField(required=False, allow_null=True)
    meta = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        txt = (attrs.get("answer_text") or "").strip()
        attrs["answer_text"] = txt or None
        if not any([attrs["answer_text"], attrs.get("answer_choice_id"), attrs.get("answer_file")]):
            raise serializers.ValidationError({"answer": ["Envía texto, opción o archivo."]})
        if attrs.get("ocr_meta") and not isinstance(attrs["ocr_meta"], dict):
            raise serializers.ValidationError({"ocr_meta": ["Debe ser dict."]})
        if attrs.get("meta") and not isinstance(attrs["meta"], dict):
            raise serializers.ValidationError({"meta": ["Debe ser dict."]})
        _validate_file(attrs.get("answer_file"), field="answer_file")
        return attrs


# ========= INPUT/OUTPUT: Save & Advance =========
class SaveAndAdvanceInputSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    user_id = serializers.UUIDField(required=False, allow_null=True)
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    answer_choice_id = serializers.UUIDField(required=False, allow_null=True)
    answer_file = serializers.FileField(required=False, allow_null=True)
    answer_file_extra = serializers.FileField(required=False, allow_null=True)
    actor_id = serializers.UUIDField(required=False, allow_null=True)
    force_truncate_future = serializers.BooleanField(required=False, default=True)
    proveedores = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        txt = (attrs.get("answer_text") or "").strip()
        attrs["answer_text"] = txt or None

        # Archivos → lista interna
        uploads: List[Any] = []
        for idx, f in enumerate([attrs.get("answer_file"), attrs.get("answer_file_extra")]):
            if f:
                _validate_file(f, field=("answer_file" if idx == 0 else "answer_file_extra"))
                uploads.append(f)

        # Proveedores: prioriza campo estructurado; luego revisa initial_data;
        # por último intenta parsear desde answer_text si es JSON-list.
        initial = self.initial_data or {}
        provs = attrs.get("proveedores", _UNSET)

        if provs is _UNSET and "proveedores" in initial:
            raw = initial.get("proveedores")
            parsed = None
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = None
            elif isinstance(raw, list):
                parsed = raw
            if isinstance(parsed, list):
                provs = [it for it in parsed if isinstance(it, dict)]

        if provs is _UNSET or provs is None:
            maybe = None
            if attrs.get("answer_text") and attrs["answer_text"].startswith("["):
                try:
                    parsed = json.loads(attrs["answer_text"])
                    if isinstance(parsed, list):
                        maybe = [it for it in parsed if isinstance(it, dict)]
                except Exception:
                    maybe = None
            if maybe:
                provs = maybe

        if provs is not _UNSET and provs is not None:
            if not isinstance(provs, list):
                raise serializers.ValidationError({"proveedores": "Debe ser una lista."})
            attrs["proveedores"] = provs

        has_any = any([
            attrs.get("answer_text"),
            attrs.get("answer_choice_id"),
            bool(uploads),
            isinstance(attrs.get("proveedores"), list),
        ])
        if not has_any:
            raise serializers.ValidationError({"answer": "Debe contener texto, opción, archivo(s) o lista de proveedores."})

        attrs["_uploads"] = uploads
        return attrs

    def to_domain_input(self):
        vd = self.validated_data
        return {
            "submission_id": vd["submission_id"],
            "question_id": vd["question_id"],
            "user_id": vd.get("user_id"),
            "answer_text": vd.get("answer_text"),
            "answer_choice_id": vd.get("answer_choice_id"),
            "uploads": vd.get("_uploads", []),
            "actor_id": vd.get("actor_id"),
            "force_truncate_future": vd.get("force_truncate_future", True),
            "proveedores": vd.get("proveedores"),
        }


class SaveAndAdvanceResponseSerializer(serializers.Serializer):
    saved_answer = serializers.SerializerMethodField()
    next_question_id = serializers.UUIDField(read_only=True, allow_null=True)
    is_finished = serializers.BooleanField(read_only=True)
    derived_updates = serializers.JSONField(read_only=True)
    warnings = serializers.ListField(child=serializers.CharField(), read_only=True)

    def get_saved_answer(self, obj) -> Optional[Dict[str, Any]]:
        saved = getattr(obj, "saved_answer", None) if hasattr(obj, "__dict__") else obj.get("saved_answer")
        return AnswerReadSerializer(saved, context=self.context).data if saved is not None else None


# ========= Verification (OCR) =========
class VerificationInputSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=["text", "document"], required=False, default="text")
    imagen = serializers.ImageField()

    def validate_imagen(self, f):
        if not f:
            raise serializers.ValidationError("La imagen es obligatoria.")
        _validate_file(f, field="imagen", types={"image/jpeg", "image/png"}, max_mb=10)
        return f


class VerificationResponseSerializer(serializers.Serializer):
    ocr_raw = serializers.CharField(read_only=True)
    placa = serializers.CharField(read_only=True, allow_null=True)
    precinto = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    valido = serializers.BooleanField(read_only=True)
    semantic_tag = serializers.CharField(read_only=True, allow_null=True)


# ========= SubmissionCreate (lo pedían las vistas) =========
class SubmissionCreateSerializer(serializers.Serializer):
    """
    Crea submissions (minimal, compatible con tus vistas).
    Acepta `questionnaire` o `questionnaire_id`, normaliza a `questionnaire_id`.
    """
    questionnaire = serializers.UUIDField(required=False)
    questionnaire_id = serializers.UUIDField(required=False)
    tipo_fase = serializers.ChoiceField(choices=["entrada", "salida"])
    regulador_id = serializers.UUIDField(required=False, allow_null=True)
    placa_vehiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        qid = attrs.get("questionnaire") or attrs.get("questionnaire_id")
        if not qid:
            raise serializers.ValidationError({"questionnaire": ["Este campo es obligatorio."]})
        # Normalizar: DRF ya valida UUIDs — copiamos al alias preferido
        attrs["questionnaire_id"] = qid
        attrs.pop("questionnaire", None)

        placa = attrs.get("placa_vehiculo")
        if placa is not None:
            placa = str(placa).strip()
            attrs["placa_vehiculo"] = placa or None
        return attrs


# ========= Submission (read) + actores y respuestas =========
class ActorModelSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    tipo = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True, allow_null=True)
    nit = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance):
        doc = getattr(instance, "documento", None)
        return {
            "id": getattr(instance, "id", None),
            "tipo": getattr(instance, "tipo", None),
            "nombre": getattr(instance, "nombre", ""),
            "documento": doc,
            "nit": doc,
        }


class SubmissionModelSerializer(SafeGetMixin, serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    questionnaire = serializers.UUIDField(read_only=True)
    questionnaire_id = serializers.UUIDField(read_only=True)
    tipo_fase = serializers.CharField(read_only=True)
    regulador_id = serializers.UUIDField(read_only=True, allow_null=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    finalizado = serializers.BooleanField(read_only=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    precinto = serializers.CharField(read_only=True, allow_null=True)

    placa_vehiculo = serializers.SerializerMethodField()
    proveedor_id = serializers.SerializerMethodField()
    transportista_id = serializers.SerializerMethodField()
    receptor_id = serializers.SerializerMethodField()
    proveedor = serializers.SerializerMethodField()
    transportista = serializers.SerializerMethodField()
    receptor = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    def get_placa_vehiculo(self, obj) -> Optional[str]:
        direct = self._get(obj, "placa_vehiculo")
        if direct:
            p = _norm_placa(direct)
            if p and p != "NO_DETECTADA":
                return p
        sid = self._get(obj, "id")
        for a in reversed(self.context.get("answers_data", {}).get(str(sid), [])):
            t = (a.get("answer_text") or "").strip()
            if not t:
                continue
            q = a.get("question") or {}
            if q.get("semantic_tag") == "placa":
                p = _norm_placa(t)
                if p != "NO_DETECTADA":
                    return p
        for a in reversed(self.context.get("answers_data", {}).get(str(sid), [])):
            t = (a.get("answer_text") or "").strip()
            if not t:
                continue
            p = _norm_placa(t)
            if p != "NO_DETECTADA":
                return p
        return None

    def get_proveedor_id(self, obj):      return self._get(obj, "proveedor_id") or self._rel_id(obj, "proveedor")
    def get_transportista_id(self, obj):  return self._get(obj, "transportista_id") or self._rel_id(obj, "transportista")
    def get_receptor_id(self, obj):       return self._get(obj, "receptor_id") or self._rel_id(obj, "receptor")

    def _actor_repr(self, rel):
        if not rel:
            return None
        return ActorModelSerializer().to_representation(rel)

    def get_proveedor(self, obj):     return self._actor_repr(self._get(obj, "proveedor"))
    def get_transportista(self, obj): return self._actor_repr(self._get(obj, "transportista"))
    def get_receptor(self, obj):      return self._actor_repr(self._get(obj, "receptor"))

    def get_answers(self, obj):
        answers = self._get(obj, "answers")
        if hasattr(answers, "all"):
            answers = answers.all()
        if answers:
            return AnswerReadSerializer(answers, many=True, context=self.context).data
        sid = self._get(obj, "id")
        data = self.context.get("answers_data", {}).get(str(sid), [])
        return AnswerReadSerializer(data, many=True, context=self.context).data


# ========= Listas pequeñas =========
class QuestionnaireListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    version = serializers.CharField()


class HistorialItemSerializer(serializers.Serializer):
    regulador_id = serializers.UUIDField(read_only=True)
    placa_vehiculo = serializers.CharField(read_only=True, allow_null=True)
    contenedor = serializers.CharField(read_only=True, allow_null=True)
    ultima_fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    fase1 = serializers.SerializerMethodField()
    fase2 = serializers.SerializerMethodField()

    def get_fase1(self, obj):
        from_obj = obj["fase1"] if isinstance(obj, dict) else getattr(obj, "fase1", None)
        return SubmissionModelSerializer(context=self.context).to_representation(from_obj) if from_obj else None

    def get_fase2(self, obj):
        from_obj = obj["fase2"] if isinstance(obj, dict) else getattr(obj, "fase2", None)
        return SubmissionModelSerializer(context=self.context).to_representation(from_obj) if from_obj else None
