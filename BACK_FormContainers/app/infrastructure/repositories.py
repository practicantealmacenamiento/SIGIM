# -*- coding: utf-8 -*-
"""
Implementaciones Django de los repositorios del dominio.

Objetivo:
- Traducir entre entidades de dominio y modelos Django (mapeos explícitos).
- Encapsular consultas/operaciones específicas de persistencia (prefetch, select_related,
  subconsultas, transacciones).

Lineamientos:
- No incluir lógica de negocio (queda en dominio / aplicación).
- Mantener APIs de los Protocols definidos en `app.domain.repositories`.
- Documentar decisiones de performance (prefetch/select_related, índices, atomic).

Repositorios implementados:
- DjangoAnswerRepository
- DjangoSubmissionRepository
- DjangoQuestionRepository
- DjangoChoiceRepository
- DjangoActorRepository
- DjangoQuestionnaireRepository
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import timedelta

# ── Django ORM ─────────────────────────────────────────────────────────────────
from django.utils import timezone
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Subquery, Q

# ── Entidades de dominio ──────────────────────────────────────────────────────
from app.domain.entities import (
    Answer as DAnswer,
    Submission as DSubmission,
    Questionnaire as DQn,
    Question as DQ,
    Choice as DC,
)

# ── Puertos de repositorio (Protocol) ─────────────────────────────────────────
from app.domain.repositories import (
    ActorRepository,
    AnswerRepository,
    ChoiceRepository,
    QuestionRepository,
    QuestionnaireRepository,
    SubmissionRepository,
    UserPK,
)

# ── Modelos Django ────────────────────────────────────────────────────────────
from app.infrastructure.models import (
    Answer as AnswerModel,
    Submission as SubmissionModel,
    Question as QuestionModel,
    Choice as ChoiceModel,
    Actor as ActorModel,
    Questionnaire as QuestionnaireModel,
)

# ==============================================================================
#   Answer (implementación Django)
# ==============================================================================

class DjangoAnswerRepository(AnswerRepository):
    """
    Repositorio de Answer basado en Django ORM.

    Responsabilidades:
    - Upsert por ID (compat con esquema original: answer_file/meta/timestamp).
    - Operaciones de consulta por usuario, submission y pregunta.
    - Limpieza de respuestas en flujos de "Guardar & Avanzar".
    - Eliminación segura de archivos asociados.
    """

    @transaction.atomic
    def save(self, answer: DAnswer) -> DAnswer:
        """
        Upsert por ID. Compatible con el esquema antiguo (answer_file/meta/timestamp).
        Si existe → `select_for_update` y actualización; si no → creación.

        Returns:
            Entidad de dominio persistida (rehidratada).
        """
        try:
            am = AnswerModel.objects.select_for_update().get(id=answer.id)
            self._update_model_from_entity(am, answer)
            am.save()
        except AnswerModel.DoesNotExist:
            am = self._create_model_from_entity(answer)
        return self._model_to_entity(am)

    def get(self, id: UUID) -> Optional[DAnswer]:
        """
        Obtiene una Answer por ID con relaciones mínimas para lectura.
        """
        am = (
            AnswerModel.objects
            .select_related("submission", "question", "answer_choice", "user")
            .filter(id=id)
            .first()
        )
        return self._model_to_entity(am) if am else None

    @transaction.atomic
    def delete(self, id: UUID) -> None:
        """
        Elimina una Answer y, si tiene archivo, borra el recurso físico (best-effort).
        """
        am = AnswerModel.objects.filter(id=id).first()
        if not am:
            return
        if getattr(am, "answer_file", None):
            am.answer_file.delete(save=False)
        am.delete()

    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[DAnswer]:
        """
        Lista respuestas por usuario, ordenadas por timestamp descendente.
        """
        qs = (
            AnswerModel.objects.filter(user_id=user_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("-timestamp")
        )
        if limit:
            qs = qs[:limit]
        return [self._model_to_entity(x) for x in qs]

    def list_by_submission(self, submission_id: UUID) -> List[DAnswer]:
        """
        Lista respuestas de una submission (orden cronológico ascendente).
        """
        qs = (
            AnswerModel.objects
            .filter(submission_id=submission_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

    def list_by_question(self, question_id: UUID) -> List[DAnswer]:
        """
        Lista respuestas por pregunta (en cualquier submission), ordenadas por tiempo.
        """
        qs = (
            AnswerModel.objects
            .filter(question_id=question_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

    # ---- Utilidades de performance para merge por submission+pregunta ----

    def list_by_submission_question(self, *, submission_id: UUID, question_id: UUID) -> List[DAnswer]:
        """
        Devuelve sólo las respuestas de una pregunta dentro de un submission.

        Útil para optimizar operaciones de merge sin traer todas las respuestas
        del submission completo.
        """
        qs = (
            AnswerModel.objects
            .filter(submission_id=submission_id, question_id=question_id)
            .select_related("submission", "question", "answer_choice")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

    @transaction.atomic
    def save_many(self, answers: List[DAnswer]) -> List[DAnswer]:
        """
        Guarda en lote (fallback a `save` uno a uno). La implementación concreta
        podría optimizar con bulk_create/bulk_update si el modelo/flujo lo permite.
        """
        out: List[DAnswer] = []
        for a in answers:
            out.append(self.save(a))
        return out

    # ---- Helpers internos ----

    def _delete_queryset(self, qs) -> int:
        """
        Elimina respuestas del queryset, cuidando el borrado físico de archivos.
        Retorna la cantidad eliminada.
        """
        count = 0
        for am in qs:
            if getattr(am, "answer_file", None):
                am.answer_file.delete(save=False)
            am.delete()
            count += 1
        return count

    # ---- Operaciones específicas del flujo Guardar&Avanzar ----

    @transaction.atomic
    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """
        Elimina respuestas de ESA pregunta dentro del submission (idempotente).
        Retorna cantidad de filas eliminadas.
        """
        qs = list(
            AnswerModel.objects.filter(
                submission_id=submission_id,
                question_id=question_id,
            )
        )
        return self._delete_queryset(qs)

    @transaction.atomic
    def delete_after_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """
        Elimina respuestas de preguntas posteriores (navegación lineal).
        Retorna cantidad de filas eliminadas.
        """
        q = QuestionModel.objects.filter(id=question_id).only("questionnaire_id", "order").first()
        if not q:
            return 0
        qs = list(
            AnswerModel.objects.filter(
                submission_id=submission_id,
                question__questionnaire_id=q.questionnaire_id,
                question__order__gt=q.order,
            ).select_related("question")
        )
        return self._delete_queryset(qs)

    # ---- Mapeos entidad/modelo ----

    def _model_to_entity(self, am: AnswerModel) -> DAnswer:
        """
        Map: AnswerModel → Answer (dominio).

        Notas:
        - `answer_file_path` se toma de `answer_file.name` si existe.
        - `timestamp` se respeta desde el modelo (campo legacy).
        """
        return DAnswer.rehydrate(
            id=am.id,
            submission_id=am.submission_id,
            question_id=am.question_id,
            user_id=getattr(am, "user_id", None),
            answer_text=am.answer_text,
            answer_choice_id=am.answer_choice_id,
            answer_file_path=(am.answer_file.name if getattr(am, "answer_file", None) else None),
            ocr_meta=getattr(am, "ocr_meta", {}) or {},
            meta=am.meta or {},
            timestamp=getattr(am, "timestamp", None),
        )

    def _create_model_from_entity(self, answer: DAnswer) -> AnswerModel:
        """
        Crea AnswerModel desde entidad de dominio (campos legacy incluidos).
        """
        return AnswerModel.objects.create(
            id=answer.id,
            submission_id=answer.submission_id,
            question_id=answer.question_id,
            user_id=getattr(answer, "user_id", None),
            answer_text=answer.answer_text,
            answer_choice_id=answer.answer_choice_id,
            answer_file=answer.answer_file_path or None,
            ocr_meta=answer.ocr_meta or {},
            meta=answer.meta or {},
            timestamp=answer.timestamp,
        )

    def _update_model_from_entity(self, am: AnswerModel, answer: DAnswer) -> None:
        """
        Actualiza un AnswerModel existente con datos de la entidad.
        """
        am.submission_id = answer.submission_id
        am.question_id = answer.question_id
        am.answer_text = answer.answer_text
        am.answer_choice_id = answer.answer_choice_id
        if hasattr(am, "user_id"):
            am.user_id = getattr(answer, "user_id", None)
        am.answer_file = answer.answer_file_path or None
        am.ocr_meta = answer.ocr_meta or {}
        am.meta = answer.meta or {}
        am.timestamp = answer.timestamp


# ==============================================================================
#   Submission (implementación Django)
# ==============================================================================

class DjangoSubmissionRepository(SubmissionRepository):
    """
    Repositorio de Submission con utilidades para API y agregaciones históricas.
    """

    def get(self, id: UUID) -> Optional[DSubmission]:
        model = SubmissionModel.objects.filter(id=id).first()
        return self._model_to_entity(model) if model else None

    def save(self, submission: DSubmission) -> DSubmission:
        """
        Upsert de submission (crea/actualiza según corresponda).
        """
        try:
            model = SubmissionModel.objects.get(id=submission.id)
            self._update_model_from_entity(model, submission)
            model.save()
        except SubmissionModel.DoesNotExist:
            model_data = self._entity_to_model_data(submission)
            model = SubmissionModel.objects.create(**model_data)
        return self._model_to_entity(model)

    def save_partial_updates(self, id: UUID, **fields) -> None:
        """
        Actualización parcial de campos (evita sobreescrituras no intencionales).
        """
        if not fields:
            return
        sub = SubmissionModel.objects.filter(id=id).first()
        if not sub:
            return
        for k, v in fields.items():
            setattr(sub, k, v)
        sub.save(update_fields=list(fields.keys()))

    # ---- Utilidades adicionales para interfaces/casos de uso ----

    def find_recent_draft_without_answers(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID],
        minutes: int = 10,
    ) -> Optional[DSubmission]:
        """
        Busca un borrador reciente (sin respuestas) para reusar.
        Límite temporal configurable vía `minutes`.
        """
        since = timezone.now() - timedelta(minutes=minutes)
        qs = SubmissionModel.objects.filter(
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            finalizado=False,
            fecha_creacion__gte=since,
        )
        if regulador_id is not None:
            qs = qs.filter(regulador_id=regulador_id)
        answers_exists = AnswerModel.objects.filter(submission_id=OuterRef("pk"))
        qs = qs.annotate(has_answers=Exists(answers_exists)).filter(has_answers=False)
        model = qs.order_by("-fecha_creacion").first()
        return self._model_to_entity(model) if model else None

    def create_submission(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID] = None,
        placa_vehiculo: Optional[str] = None,
    ) -> DSubmission:
        """
        Crea una nueva submission y asegura la coherencia de `regulador_id`.
        """
        obj = SubmissionModel.objects.create(
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
        )
        self.ensure_regulador_on_create(obj)
        return self._model_to_entity(obj)

    def get_fase1_by_regulador(self, regulador_id: UUID) -> Optional[DSubmission]:
        """
        Obtiene la última Fase 1 (entrada) finalizada para un regulador.
        """
        model = (
            SubmissionModel.objects.filter(regulador_id=regulador_id, tipo_fase="entrada")
            .order_by("-fecha_cierre", "-fecha_creacion")
            .first()
        )
        return self._model_to_entity(model) if model else None

    def set_regulador(self, submission_id: UUID, regulador_id: UUID) -> None:
        """
        Asigna/actualiza el `regulador_id` de una submission.
        """
        SubmissionModel.objects.filter(id=submission_id).update(regulador_id=regulador_id)

    # ---- Consultas para vistas de API ----

    def list_for_api(self, params):
        """
        Retorna queryset de submissions con relaciones y filtros aplicables
        (pensado para vistas de listado). No evalúa el queryset.
        """
        qs = (
            SubmissionModel.objects.all()
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
            .order_by("-fecha_creacion")
            .prefetch_related("answers")
        )
        p = params

        if not p.get("incluir_borradores"):
            qs = qs.filter(finalizado=True)
        if p.get("solo_finalizados") in ("1", "true", "True"):
            qs = qs.filter(finalizado=True)

        if p.get("tipo_fase"):
            qs = qs.filter(tipo_fase=p["tipo_fase"])
        if p.get("placa_vehiculo"):
            qs = qs.filter(placa_vehiculo__icontains=p["placa_vehiculo"])
        if p.get("contenedor"):
            qs = qs.filter(contenedor__icontains=p["contenedor"])
        if p.get("proveedor_id"):
            qs = qs.filter(proveedor_id=p["proveedor_id"])
        if p.get("transportista_id"):
            qs = qs.filter(transportista_id=p["transportista_id"])
        if p.get("receptor_id"):
            qs = qs.filter(receptor_id=p["receptor_id"])

        if p.get("fecha_desde"):
            qs = qs.filter(fecha_cierre__date__gte=p["fecha_desde"])
        if p.get("fecha_hasta"):
            qs = qs.filter(fecha_cierre__date__lte=p["fecha_hasta"])

        # Pendientes de fase 2 (cuando se listan entradas que aún no tienen salida final)
        if p.get("solo_pendientes_fase2") in ("1", "true", "True") and p.get("tipo_fase") == "entrada":
            fase2 = SubmissionModel.objects.filter(
                tipo_fase="salida",
                finalizado=True,
                regulador_id__isnull=False,
                regulador_id=OuterRef("regulador_id"),
            )
            qs = qs.annotate(has_salida_final=Exists(fase2)).filter(has_salida_final=False)
            qs = qs.prefetch_related("answers__question", "answers__answer_choice")

        return qs

    def ensure_regulador_on_create(self, obj: SubmissionModel) -> None:
        """
        Asegura coherencia de `regulador_id` entre Fase 1 (entrada) y Fase 2 (salida).

        Reglas:
        - Si es entrada y no trae regulador_id → se setea a su propio id.
        - Si es salida y trae regulador_id → asegura que la entrada correspondiente
          tenga el mismo regulador_id.
        """
        if obj.tipo_fase == "entrada" and not obj.regulador_id:
            obj.regulador_id = obj.id
            obj.save(update_fields=["regulador_id"])
            return

        if obj.tipo_fase == "salida" and obj.regulador_id:
            entrada = SubmissionModel.objects.filter(id=obj.regulador_id, tipo_fase="entrada").first()
            if entrada and entrada.regulador_id != obj.regulador_id:
                entrada.regulador_id = obj.regulador_id
                entrada.save(update_fields=["regulador_id"])

    # ---- Detalle con relaciones (para serialización completa) ----

    def detail_queryset(self):
        """
        Retorna un queryset de submissions con respuestas + preguntas + choice prefetch-eados.
        """
        answers_qs = (
            AnswerModel.objects
            .select_related("question", "answer_choice")
            .order_by("timestamp")
        )
        return (
            SubmissionModel.objects
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
            .prefetch_related(Prefetch("answers", queryset=answers_qs))
        )

    def get_detail(self, id: UUID) -> Optional[DSubmission]:
        """
        Obtiene una submission con relaciones precargadas y la mapea a dominio.
        """
        model = self.detail_queryset().filter(id=id).first()
        return self._model_to_entity(model) if model else None

    def get_for_api(self, id: UUID):
        """
        Devuelve el modelo Django de Submission con relaciones y respuestas
        prefetch-eadas para serialización en la API (sin mapear a dominio).
        """
        return self.detail_queryset().filter(id=id).first()

    # ---- Agregación de historial ----

    def history_aggregate(self, *, fecha_desde=None, fecha_hasta=None):
        """
        Agrega por `regulador_id` las últimas fases (F1/F2) y la última fecha de cierre.

        Retorna queryset de dicts:
            {
              regulador_id, fase1_id, fase2_id, ultima_fecha_cierre
            }
        """
        base = SubmissionModel.objects.filter(regulador_id__isnull=False, finalizado=True)

        if fecha_desde:
            base = base.filter(fecha_cierre__date__gte=fecha_desde)
        if fecha_hasta:
            base = base.filter(fecha_cierre__date__lte=fecha_hasta)

        last_f1 = (
            SubmissionModel.objects.filter(
                regulador_id=OuterRef("regulador_id"),
                finalizado=True,
                tipo_fase="entrada",
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("id")[:1]
        )
        last_f2 = (
            SubmissionModel.objects.filter(
                regulador_id=OuterRef("regulador_id"),
                finalizado=True,
                tipo_fase="salida",
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("id")[:1]
        )
        last_date = (
            SubmissionModel.objects.filter(
                regulador_id=OuterRef("regulador_id"),
                finalizado=True,
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("fecha_cierre")[:1]
        )

        return (
            base.values("regulador_id")
            .annotate(
                fase1_id=Subquery(last_f1),
                fase2_id=Subquery(last_f2),
                ultima_fecha_cierre=Subquery(last_date),
            )
            .distinct()
            .order_by("-ultima_fecha_cierre")
        )

    def get_by_ids(self, ids):
        """
        Retorna un dict {str(id): SubmissionModel} para los ids solicitados
        (con relaciones select_related relevantes).
        """
        qs = (
            SubmissionModel.objects.filter(id__in=ids)
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
        )
        return {str(s.id): s for s in qs}

    # ---- Mapeos entidad/modelo ----

    def _model_to_entity(self, model: SubmissionModel) -> DSubmission:
        """
        Map: SubmissionModel → Submission (dominio).
        """
        return DSubmission(
            id=model.id,
            questionnaire_id=model.questionnaire_id,
            tipo_fase=model.tipo_fase,
            regulador_id=model.regulador_id,
            placa_vehiculo=model.placa_vehiculo,
            finalizado=model.finalizado,
            fecha_creacion=model.fecha_creacion,
            fecha_cierre=model.fecha_cierre,
        )

    def _entity_to_model_data(self, entity: DSubmission) -> Dict[str, Any]:
        """
        Map: Submission (dominio) → dict de campos para crear SubmissionModel.
        """
        return {
            "id": entity.id,
            "questionnaire_id": entity.questionnaire_id,
            "tipo_fase": entity.tipo_fase,
            "regulador_id": entity.regulador_id,
            "placa_vehiculo": entity.placa_vehiculo,
            "finalizado": entity.finalizado,
            "fecha_creacion": entity.fecha_creacion,
            "fecha_cierre": entity.fecha_cierre,
        }

    def _update_model_from_entity(self, model: SubmissionModel, entity: DSubmission) -> None:
        """
        Actualiza un SubmissionModel con datos de la entidad.
        """
        model.questionnaire_id = entity.questionnaire_id
        model.tipo_fase = entity.tipo_fase
        model.regulador_id = entity.regulador_id
        model.placa_vehiculo = entity.placa_vehiculo
        model.finalizado = entity.finalizado
        model.fecha_creacion = entity.fecha_creacion
        model.fecha_cierre = entity.fecha_cierre


# ==============================================================================
#   Question (implementación Django)
# ==============================================================================

class DjangoQuestionRepository(QuestionRepository):
    """
    Repositorio de preguntas con utilidades de navegación (siguiente por orden).
    """

    def get(self, id: UUID) -> Optional[DQ]:
        model = QuestionModel.objects.filter(id=id).prefetch_related("choices").first()
        return self._model_to_entity(model) if model else None

    def list_by_questionnaire(self, questionnaire_id: UUID) -> List[DQ]:
        models = list(
            QuestionModel.objects
            .filter(questionnaire_id=questionnaire_id)
            .order_by("order")
            .prefetch_related("choices")
        )
        return [self._model_to_entity(model) for model in models]

    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]:
        """
        Obtiene el ID de la siguiente pregunta por orden dentro del mismo cuestionario.
        """
        q = QuestionModel.objects.filter(id=current_question_id).only("questionnaire_id", "order").first()
        if not q:
            return None
        next_q = (
            QuestionModel.objects.filter(
                questionnaire_id=q.questionnaire_id,
                order__gt=q.order,
            )
            .order_by("order")
            .only("id")
            .first()
        )
        return next_q.id if next_q else None

    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[DQ]:
        """
        Fallback: encuentra la siguiente pregunta por `order` dado.
        """
        model = (
            QuestionModel.objects.filter(questionnaire_id=questionnaire_id, order__gt=order)
            .order_by("order")
            .prefetch_related("choices")
            .first()
        )
        return self._model_to_entity(model) if model else None

    def get_by_id(self, id: str) -> Optional[QuestionModel]:
        """
        Retorna el modelo Question por id (UUID en str) o None si no existe.
        No lanza excepción hacia la vista (útil para endpoints).
        """
        try:
            return QuestionModel.objects.get(id=id)
        except QuestionModel.DoesNotExist:
            return None

    # ---- Mapeo ----

    def _model_to_entity(self, model: QuestionModel) -> DQ:
        """
        Map: QuestionModel → Question (dominio), incluyendo choices sólo si aplica.
        """
        choices = []
        if model.type == "choice" and hasattr(model, "choices"):
            for choice_model in model.choices.all():
                choices.append(
                    DC(
                        id=choice_model.id,
                        text=choice_model.text,
                        branch_to=choice_model.branch_to_id,
                    )
                )

        return DQ(
            id=model.id,
            text=model.text,
            type=model.type,
            required=model.required,
            order=model.order,
            choices=tuple(choices) if choices else None,
            semantic_tag=model.semantic_tag,
            file_mode=model.file_mode,
        )


# ==============================================================================
#   Choice (implementación Django)
# ==============================================================================

class DjangoChoiceRepository(ChoiceRepository):
    """Repositorio mínimo de opciones de pregunta."""

    def get(self, id: UUID) -> Optional[DC]:
        model = ChoiceModel.objects.filter(id=id).only("id", "text", "branch_to").first()
        return self._model_to_entity(model) if model else None

    def _model_to_entity(self, model: ChoiceModel) -> DC:
        """Map: ChoiceModel → Choice (dominio)."""
        return DC(id=model.id, text=model.text, branch_to=model.branch_to_id)


# ==============================================================================
#   Actors (consultas públicas/admin para catálogos)
# ==============================================================================

class DjangoActorRepository(ActorRepository):
    """
    Repositorio para catálogo de actores (proveedor/transportista/receptor).
    Retorna modelos Django para uso directo con serializers manuales.
    """

    def get(self, id: UUID):
        try:
            obj = ActorModel.objects.get(id=id, activo=True)
            return obj
        except ActorModel.DoesNotExist:
            return None

    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50):
        qs = ActorModel.objects.filter(activo=True, tipo=tipo)
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))
        return list(qs.order_by("nombre")[:limit])

    def public_list(self, params):
        """
        Listado público con filtros básicos (tipo, search) y tope de 50 elementos.
        """
        qs = ActorModel.objects.filter(activo=True)
        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        search = params.get("search")
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))

        return qs.order_by("nombre")[:50]

    def admin_queryset(self, params):
        """
        QuerySet para vistas de administración con filtros por tipo/activo/búsqueda.
        """
        qs = ActorModel.objects.all().order_by("nombre")
        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        activo = params.get("activo")
        if activo in ("1", "true", "True"):
            qs = qs.filter(activo=True)
        search = params.get("search")
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontincontains=search))
        return qs


# ==============================================================================
#   Questionnaire (implementación completa para uso en admin)
# ==============================================================================

class DjangoQuestionnaireRepository(QuestionnaireRepository):
    """
    Repositorio de Cuestionarios para admin (dominio) y selector público.

    Provee:
      - list_all() / get_by_id() / save()  -> para AdminQuestionnaireViewSet
      - list_minimal()                      -> para selector público
    """

    # ---- Mapeo explícito de modelo a dominio ----

    def _model_to_entity(self, qn: QuestionnaireModel) -> DQn:
        """
        Map: QuestionnaireModel → Questionnaire (dominio), con sus preguntas/choices.
        """
        questions = []
        for q in qn.questions.all().order_by("order").prefetch_related("choices"):
            choices = []
            if q.type == "choice":
                choices = [
                    DC(id=c.id, text=c.text, branch_to=(c.branch_to_id or None))
                    for c in q.choices.all()
                ]

            questions.append(
                DQ(
                    id=q.id,
                    text=q.text,
                    type=q.type,
                    required=q.required,
                    order=q.order,
                    choices=tuple(choices) if choices else None,
                    semantic_tag=q.semantic_tag,
                    file_mode=q.file_mode,
                )
            )
        return DQn(
            id=qn.id,
            title=qn.title,
            version=qn.version,
            timezone=qn.timezone,
            questions=tuple(questions),
        )

    # ---- API Admin (dominio) ----

    def list_all(self) -> List[DQn]:
        """
        Lista todos los cuestionarios con sus preguntas y opciones ya prefetch-eadas.
        """
        qs = (
            QuestionnaireModel.objects
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=QuestionModel.objects.order_by("order").prefetch_related("choices"),
                )
            )
            .order_by("title", "version")
        )
        return [self._model_to_entity(x) for x in qs]

    def get_by_id(self, id: UUID) -> Optional[DQn]:
        """
        Obtiene un cuestionario por ID con su árbol de preguntas/choices prefetch-eado.
        """
        qn = (
            QuestionnaireModel.objects
            .filter(id=id)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=QuestionModel.objects.order_by("order").prefetch_related("choices"),
                )
            )
            .first()
        )
        return self._model_to_entity(qn) if qn else None

    @transaction.atomic
    def save(self, dq: DQn) -> DQn:
        """
        Upsert de cuestionario + sincronización de preguntas y choices asociados.

        Estrategia:
        - update_or_create para el cuestionario.
        - Borrado de preguntas que ya no están presentes.
        - Upsert de preguntas.
        - Borrado de choices faltantes por pregunta.
        - Upsert de choices (permite `branch_to` a cualquier pregunta existente).
        """
        # Upsert del cuestionario
        qn, _created = QuestionnaireModel.objects.update_or_create(
            id=dq.id,
            defaults={
                "title": dq.title,
                "version": dq.version,
                "timezone": dq.timezone,
            },
        )

        # Sincronizar preguntas (upsert + delete faltantes)
        incoming_q_ids = {q.id for q in dq.questions}
        for orm_q in QuestionModel.objects.filter(questionnaire=qn):
            if orm_q.id not in incoming_q_ids:
                orm_q.delete()

        # Upsert preguntas base
        for q in dq.questions:
            orm_q, _ = QuestionModel.objects.update_or_create(
                id=q.id,
                defaults={
                    "questionnaire": qn,
                    "text": q.text,
                    "type": q.type,
                    "required": q.required,
                    "order": q.order,
                    "semantic_tag": q.semantic_tag or "none",
                    "file_mode": q.file_mode or "image_only",
                },
            )

            # Sincronizar choices de la pregunta
            incoming_c_ids = {c.id for c in (q.choices or [])}
            for orm_c in ChoiceModel.objects.filter(question=orm_q):
                if orm_c.id not in incoming_c_ids:
                    orm_c.delete()

            # Upsert choices
            for c in (q.choices or []):
                branch_target = None
                if c.branch_to:
                    # Permite branch a cualquier pregunta existente (se asume misma encuesta)
                    branch_target = QuestionModel.objects.filter(id=c.branch_to).first()
                ChoiceModel.objects.update_or_create(
                    id=c.id,
                    defaults={
                        "question": orm_q,
                        "text": c.text,
                        "branch_to": branch_target,
                    },
                )

        # Recargar con relaciones y devolver en dominio
        qn = (
            QuestionnaireModel.objects
            .filter(id=qn.id)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=QuestionModel.objects.order_by("order").prefetch_related("choices"),
                )
            )
            .first()
        )
        return self._model_to_entity(qn)

    # ---- API pública (selector) ----

    def list_minimal(self):
        """
        Listado mínimo de cuestionarios (id, title, version) para selectores UI.
        """
        return (
            QuestionnaireModel.objects
            .only("id", "title", "version")
            .order_by("title", "version")
        )

    @transaction.atomic
    def delete(self, id: UUID) -> bool:
        """
        Elimina un cuestionario por ID.

        Returns:
            True si se eliminó alguna fila; False si no se encontró.
        """
        try:
            deleted_count, _ = QuestionnaireModel.objects.filter(id=id).delete()
            return deleted_count > 0
        except Exception:
            return False
