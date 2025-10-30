# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch

from app.domain.entities import Questionnaire as DQn, Question as DQ, Choice as DC
from app.domain.ports.repositories import QuestionnaireRepository

from app.infrastructure.models import (
    Questionnaire as QuestionnaireModel,
    Question as QuestionModel,
    Choice as ChoiceModel,
)

class DjangoQuestionnaireRepository(QuestionnaireRepository):
    """
    Repositorio de Cuestionarios para admin (dominio) y selector público.
    """

    def _model_to_entity(self, qn: QuestionnaireModel) -> DQn:
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

    def list_all(self) -> List[DQn]:
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
        qn, _created = QuestionnaireModel.objects.update_or_create(
            id=dq.id,
            defaults={
                "title": dq.title,
                "version": dq.version,
                "timezone": dq.timezone,
            },
        )

        incoming_q_ids = {q.id for q in dq.questions}
        for orm_q in QuestionModel.objects.filter(questionnaire=qn):
            if orm_q.id not in incoming_q_ids:
                orm_q.delete()

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

            incoming_c_ids = {c.id for c in (q.choices or [])}
            for orm_c in ChoiceModel.objects.filter(question=orm_q):
                if orm_c.id not in incoming_c_ids:
                    orm_c.delete()

            for c in (q.choices or []):
                branch_target = None
                if c.branch_to:
                    branch_target = QuestionModel.objects.filter(id=c.branch_to).first()
                ChoiceModel.objects.update_or_create(
                    id=c.id,
                    defaults={
                        "question": orm_q,
                        "text": c.text,
                        "branch_to": branch_target,
                    },
                )

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

    def list_minimal(self):
        return (
            QuestionnaireModel.objects
            .only("id", "title", "version")
            .order_by("title", "version")
        )

    @transaction.atomic
    def delete(self, id: UUID) -> bool:
        try:
            deleted_count, _ = QuestionnaireModel.objects.filter(id=id).delete()
            return deleted_count > 0
        except Exception:
            return False
