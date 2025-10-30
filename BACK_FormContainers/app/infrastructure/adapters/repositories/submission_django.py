# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID
from datetime import timedelta

from django.utils import timezone
from django.db.models import Exists, OuterRef, Prefetch, Subquery, Q

from app.domain.entities import Submission as DSubmission
from app.domain.ports.repositories import SubmissionRepository

from app.infrastructure.models import (
    Answer as AnswerModel,
    Submission as SubmissionModel,
    Question as QuestionModel,
)

class DjangoSubmissionRepository(SubmissionRepository):
    """
    Repositorio de Submission con utilidades para API y agregaciones históricas.
    """

    def get(self, id: UUID) -> Optional[DSubmission]:
        model = SubmissionModel.objects.filter(id=id).first()
        return self._model_to_entity(model) if model else None

    def save(self, submission: DSubmission) -> DSubmission:
        try:
            model = SubmissionModel.objects.get(id=submission.id)
            self._update_model_from_entity(model, submission)
            model.save()
        except SubmissionModel.DoesNotExist:
            model_data = self._entity_to_model_data(submission)
            model = SubmissionModel.objects.create(**model_data)
        return self._model_to_entity(model)

    def save_partial_updates(self, id: UUID, **fields) -> None:
        if not fields:
            return
        sub = SubmissionModel.objects.filter(id=id).first()
        if not sub:
            return
        for k, v in fields.items():
            setattr(sub, k, v)
        sub.save(update_fields=list(fields.keys()))

    def find_recent_draft_without_answers(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID],
        minutes: int = 10,
    ) -> Optional[DSubmission]:
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
        created_by=None,
    ) -> DSubmission:
        obj = SubmissionModel.objects.create(
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
            created_by=created_by,
        )
        self.ensure_regulador_on_create(obj)
        return self._model_to_entity(obj)

    def get_fase1_by_regulador(self, regulador_id: UUID) -> Optional[DSubmission]:
        model = (
            SubmissionModel.objects.filter(regulador_id=regulador_id, tipo_fase="entrada")
            .order_by("-fecha_cierre", "-fecha_creacion")
            .first()
        )
        return self._model_to_entity(model) if model else None

    def set_regulador(self, submission_id: UUID, regulador_id: UUID) -> None:
        SubmissionModel.objects.filter(id=submission_id).update(regulador_id=regulador_id)

    # ---- Consultas para vistas de API ----

    def _apply_user_scope(self, qs, *, user=None, include_all: bool = False):
        if include_all or user is None:
            return qs
        return qs.filter(created_by=user)

    def list_for_api(self, params, *, user=None, include_all: bool = False):
        qs = (
            SubmissionModel.objects.all()
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
            .order_by("-fecha_creacion")
            .prefetch_related("answers")
        )
        qs = self._apply_user_scope(qs, user=user, include_all=include_all)
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

    def detail_queryset(self, *, user=None, include_all: bool = False):
        answers_qs = (
            AnswerModel.objects
            .select_related("question", "answer_choice")
            .order_by("timestamp")
        )
        base_qs = (
            SubmissionModel.objects
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
            .prefetch_related(Prefetch("answers", queryset=answers_qs))
        )
        return self._apply_user_scope(base_qs, user=user, include_all=include_all)

    def get_detail(self, id: UUID, *, user=None, include_all: bool = False) -> Optional[DSubmission]:
        model = self.detail_queryset(user=user, include_all=include_all).filter(id=id).first()
        return self._model_to_entity(model) if model else None

    def get_for_api(self, id: UUID, *, user=None, include_all: bool = False):
        return self.detail_queryset(user=user, include_all=include_all).filter(id=id).first()

    # ---- Agregación de historial ----

    def history_aggregate(self, *, fecha_desde=None, fecha_hasta=None, user=None, include_all: bool = False):
        base = SubmissionModel.objects.filter(regulador_id__isnull=False, finalizado=True)
        base = self._apply_user_scope(base, user=user, include_all=include_all)

        if fecha_desde:
            base = base.filter(fecha_cierre__date__gte=fecha_desde)
        if fecha_hasta:
            base = base.filter(fecha_cierre__date__lte=fecha_hasta)

        scoped_submissions = lambda qs: self._apply_user_scope(qs, user=user, include_all=include_all)

        last_f1 = (
            scoped_submissions(
                SubmissionModel.objects.filter(
                    regulador_id=OuterRef("regulador_id"),
                    finalizado=True,
                    tipo_fase="entrada",
                )
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("id")[:1]
        )
        last_f2 = (
            scoped_submissions(
                SubmissionModel.objects.filter(
                    regulador_id=OuterRef("regulador_id"),
                    finalizado=True,
                    tipo_fase="salida",
                )
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("id")[:1]
        )
        last_date = (
            scoped_submissions(
                SubmissionModel.objects.filter(
                    regulador_id=OuterRef("regulador_id"),
                    finalizado=True,
                )
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

    def get_by_ids(self, ids, *, user=None, include_all: bool = False):
        qs = (
            SubmissionModel.objects.filter(id__in=ids)
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
        )
        qs = self._apply_user_scope(qs, user=user, include_all=include_all)
        return {str(s.id): s for s in qs}

    # ---- Mapeos ----

    def _model_to_entity(self, model: SubmissionModel) -> DSubmission:
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
        model.questionnaire_id = entity.questionnaire_id
        model.tipo_fase = entity.tipo_fase
        model.regulador_id = entity.regulador_id
        model.placa_vehiculo = entity.placa_vehiculo
        model.finalizado = entity.finalizado
        model.fecha_creacion = entity.fecha_creacion
        model.fecha_cierre = entity.fecha_cierre
