# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable, List, Optional
from uuid import UUID

from app.domain.entities import Question as DQ, Choice as DC
from app.domain.ports.repositories import QuestionRepository
from app.infrastructure.models import Question as QuestionModel


class DjangoQuestionRepository(QuestionRepository):
    """
    Repositorio de preguntas con utilidades de navegación (siguiente por orden).

    Notas:
    - `get(...)`, `list_by_questionnaire(...)`, `next_in_questionnaire(...)` y
      `find_next_by_order(...)` cumplen estrictamente el puerto (devuelven entidades).
    - `get_by_id(...)` (infra-only) retorna el *modelo* para vistas que serializan
      con ModelSerializers (evita re-mapear a entidad en ese flujo).
    - `list_by_ids(...)` es opcional (usado por servicios para rehidratar más eficiente).
    """

    # ============================
    # Métodos del puerto (entidad)
    # ============================

    def get(self, id: UUID) -> Optional[DQ]:
        model = (
            QuestionModel.objects
            .filter(id=id)
            .prefetch_related("choices")
            .first()
        )
        return self._model_to_entity(model) if model else None

    def list_by_questionnaire(self, questionnaire_id: UUID) -> List[DQ]:
        models = list(
            QuestionModel.objects
            .filter(questionnaire_id=questionnaire_id)
            .order_by("order")
            .prefetch_related("choices")
        )
        return [self._model_to_entity(m) for m in models]

    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]:
        q = (
            QuestionModel.objects
            .filter(id=current_question_id)
            .only("questionnaire_id", "order")
            .first()
        )
        if not q:
            return None
        next_q = (
            QuestionModel.objects
            .filter(questionnaire_id=q.questionnaire_id, order__gt=q.order)
            .order_by("order")
            .only("id")
            .first()
        )
        return next_q.id if next_q else None

    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[DQ]:
        model = (
            QuestionModel.objects
            .filter(questionnaire_id=questionnaire_id, order__gt=order)
            .order_by("order")
            .prefetch_related("choices")
            .first()
        )
        return self._model_to_entity(model) if model else None

    # =======================================
    # Extensiones útiles (no forman parte del
    # puerto estricto pero las usa la app)
    # =======================================

    def list_by_ids(self, ids: Iterable[UUID]) -> List[DQ]:
        """
        Optimiza rehidratación en lote (service.get_detail).
        No es parte del puerto estricto; se usa con hasattr(...) en el servicio.
        """
        ids = list(ids)
        if not ids:
            return []
        models = list(
            QuestionModel.objects
            .filter(id__in=ids)
            .prefetch_related("choices")
        )
        return [self._model_to_entity(m) for m in models]

    def get_by_id(self, id: str) -> Optional[QuestionModel]:
        """
        Devuelve el *modelo* (no entidad). Solo para vistas que serializan con
        serializers de infraestructura basados en modelos.
        """
        try:
            return QuestionModel.objects.get(id=id)
        except QuestionModel.DoesNotExist:
            return None

    # ============================
    # Mapeo entidad ← modelo
    # ============================

    def _model_to_entity(self, model: QuestionModel) -> DQ:
        # Guard clause por seguridad en helpers internos
        if model is None:
            return None  # type: ignore[return-value]

        choices: List[DC] = []
        # Prefetch de 'choices' solo aplica cuando type == "choice"
        if getattr(model, "type", None) == "choice" and hasattr(model, "choices"):
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
            semantic_tag=getattr(model, "semantic_tag", None),
            file_mode=getattr(model, "file_mode", None),
        )

