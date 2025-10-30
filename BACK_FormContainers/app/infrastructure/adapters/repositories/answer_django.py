# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from django.db import transaction

from app.domain.entities import Answer as DAnswer
from app.domain.ports.repositories import AnswerRepository, UserPK

from app.infrastructure.models import (
    Answer as AnswerModel,
    Question as QuestionModel,
)


class DjangoAnswerRepository(AnswerRepository):
    """
    Repositorio de Answer basado en Django ORM.

    Notas de diseño:
    - La capa de aplicación se encarga de almacenar el archivo y proveer el path;
      aquí solo se asigna `answer_file` con el path relativo (string) o None.
    - Se usan transacciones en operaciones que modifican múltiples filas/recursos
      (p. ej., clear/delete_after_question) y en `save` por consistencia.
    """

    @transaction.atomic
    def save(self, answer: DAnswer) -> DAnswer:
        """
        Crea/actualiza Answer.
        - Si existe, se bloquea la fila con SELECT FOR UPDATE para evitar condiciones de carrera.
        - Si no existe, se crea con los datos del entity.
        """
        try:
            am = AnswerModel.objects.select_for_update().get(id=answer.id)
            self._update_model_from_entity(am, answer)
            am.save()
        except AnswerModel.DoesNotExist:
            am = self._create_model_from_entity(answer)
        return self._model_to_entity(am)

    def get(self, id: UUID) -> Optional[DAnswer]:
        am = (
            AnswerModel.objects
            .select_related("submission", "question", "answer_choice", "user")
            .filter(id=id)
            .first()
        )
        return self._model_to_entity(am) if am else None

    @transaction.atomic
    def delete(self, id: UUID) -> None:
        am = AnswerModel.objects.filter(id=id).first()
        if not am:
            return
        # Eliminar archivo asociado si lo hay (best-effort; no falla si ya no existe)
        if getattr(am, "answer_file", None):
            am.answer_file.delete(save=False)
        am.delete()

    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[DAnswer]:
        qs = (
            AnswerModel.objects.filter(user_id=user_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("-timestamp")
        )
        if limit:
            qs = qs[: int(limit)]
        return [self._model_to_entity(x) for x in qs]

    def list_by_submission(self, submission_id: UUID) -> List[DAnswer]:
        qs = (
            AnswerModel.objects
            .filter(submission_id=submission_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

    def list_by_question(self, question_id: UUID) -> List[DAnswer]:
        qs = (
            AnswerModel.objects
            .filter(question_id=question_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

    def list_by_submission_question(self, *, submission_id: UUID, question_id: UUID) -> List[DAnswer]:
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
        Guarda en lote. Implementación simple sobre `save` para mantener
        invariantes (archivo, metadatos). Una futura optimización puede
        usar bulk_create/bulk_update si es necesario.
        """
        out: List[DAnswer] = []
        for a in answers:
            out.append(self.save(a))
        return out

    # ---- Helpers internos ----

    def _delete_queryset(self, qs) -> int:
        """
        Elimina respuestas de un queryset, limpiando los archivos asociados.
        Nota: se itera para garantizar la eliminación del archivo por fila.
        """
        count = 0
        for am in qs:
            if getattr(am, "answer_file", None):
                am.answer_file.delete(save=False)
            am.delete()
            count += 1
        return count

    @transaction.atomic
    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """
        Elimina todas las respuestas de ESA pregunta dentro del submission.
        Ojo: El caso de uso decide cuándo invocar esto (no debe usarse en la
        pregunta 'proveedor' cuando se permite multi-entrada).
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
        Elimina respuestas de preguntas posteriores dentro del mismo cuestionario
        (útil cuando se cambia una respuesta intermedia y se invalida el camino).
        """
        q = (
            QuestionModel.objects
            .filter(id=question_id)
            .only("questionnaire_id", "order")
            .first()
        )
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

    def _model_to_entity(self, am: AnswerModel) -> DAnswer:
        return DAnswer.rehydrate(
            id=am.id,
            submission_id=am.submission_id,
            question_id=am.question_id,
            user_id=getattr(am, "user_id", None),
            answer_text=am.answer_text,
            answer_choice_id=am.answer_choice_id,
            # En FileField, `.name` es el path relativo en media storage:
            answer_file_path=(am.answer_file.name if getattr(am, "answer_file", None) else None),
            ocr_meta=getattr(am, "ocr_meta", {}) or {},
            meta=am.meta or {},
            timestamp=getattr(am, "timestamp", None),
        )

    def _create_model_from_entity(self, answer: DAnswer) -> AnswerModel:
        return AnswerModel.objects.create(
            id=answer.id,
            submission_id=answer.submission_id,
            question_id=answer.question_id,
            user_id=getattr(answer, "user_id", None),
            answer_text=answer.answer_text,
            answer_choice_id=answer.answer_choice_id,
            # Asignamos el path ya guardado por FileStorage (string relativo) o None:
            answer_file=answer.answer_file_path or None,
            ocr_meta=answer.ocr_meta or {},
            meta=answer.meta or {},
            timestamp=answer.timestamp,
        )

    def _update_model_from_entity(self, am: AnswerModel, answer: DAnswer) -> None:
        am.submission_id = answer.submission_id
        am.question_id = answer.question_id
        am.answer_text = answer.answer_text
        am.answer_choice_id = answer.answer_choice_id
        if hasattr(am, "user_id"):
            am.user_id = getattr(answer, "user_id", None)
        # Igual que en create: asignamos el path (string) o None
        am.answer_file = answer.answer_file_path or None
        am.ocr_meta = answer.ocr_meta or {}
        am.meta = answer.meta or {}
        am.timestamp = answer.timestamp

