"""Entidades de dominio para el modulo de cuestionarios.

Este modulo concentra las entidades puras que describen el nucleo del dominio:
- Choice: opcion elegible dentro de una pregunta tipo choice.
- Question: pregunta del cuestionario, con orden y metadatos.
- Questionnaire: agregado que agrupa preguntas.
- Submission: envio del formulario con su estado.
- Answer: respuesta provista para una pregunta.

Reglas generales:
- No depende de frameworks ni del ORM.
- Las firmas y comportamientos expuestos no deben modificarse.
- Las validaciones implementan invariantes de dominio.

Para mantener consistencia:
- Los textos se normalizan con `_normalize_text` o `_normalize_str`.
- Las fechas se manejan en UTC mediante `datetime.now(timezone.utc)`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.domain.exceptions import (
    InvariantViolationError,
    ValidationError,
    BusinessRuleViolationError,
)

__all__ = ["Choice", "Question", "Questionnaire", "Answer", "Submission"]


# ---------------------------------------------------------------------------
# Entidades de dominio
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Choice:
    """Opcion de respuesta para una pregunta tipo choice."""

    id: UUID
    text: str
    branch_to: Optional[UUID] = None  # Ramificacion condicional

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _normalize_text(self.text) or "")
        if not self.text.strip():
            raise ValidationError(
                message="El texto de la opción no puede estar vacío.",
                field="text",
            )

    def has_branch(self) -> bool:
        """Indica si la opcion define una ramificacion."""

        return self.branch_to is not None

    def get_display_text(self) -> str:
        """Retorna el texto visible de la opcion."""

        return self.text


@dataclass(frozen=True)
class Question:
    """Pregunta del cuestionario con sus metadatos principales."""

    id: UUID
    text: str
    type: str  # text | number | date | choice | file
    required: bool
    order: int
    choices: Optional[List[Choice]] = None
    semantic_tag: Optional[str] = None
    file_mode: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _normalize_text(self.text) or "")
        object.__setattr__(self, "semantic_tag", _normalize_str(self.semantic_tag))
        object.__setattr__(self, "file_mode", _normalize_str(self.file_mode))
        if self.choices is not None:
            object.__setattr__(self, "choices", list(self.choices))
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.text.strip():
            raise ValidationError(
                message="El texto de la pregunta no puede estar vacío.",
                field="text",
            )

        if self.type not in {"text", "number", "date", "choice", "file"}:
            raise ValidationError(
                message=f"Tipo de pregunta inválido: {self.type}",
                field="type",
            )

        if self.order < 0:
            raise ValidationError(
                message="El orden de la pregunta debe ser un número positivo.",
                field="order",
            )

        if self.type == "choice" and not self.choices:
            raise ValidationError(
                message="Las preguntas de tipo 'choice' deben tener al menos una opción.",
                field="choices",
            )

        if self.type != "choice" and self.choices:
            raise ValidationError(
                message=f"Las preguntas de tipo '{self.type}' no pueden tener opciones.",
                field="choices",
            )

    # Consultas semanticas
    def is_choice_question(self) -> bool:
        return self.type == "choice"

    def is_file_question(self) -> bool:
        return self.type == "file"

    def is_text_question(self) -> bool:
        return self.type == "text"

    def is_required(self) -> bool:
        return self.required

    def has_ocr_capability(self) -> bool:
        return self.file_mode in {"image_ocr", "image_dual"}

    def is_proveedor(self) -> bool:
        tag = (self.semantic_tag or "").strip().upper()
        return tag in {"PROVEEDOR", "PROVEEDORES"}

    def get_choice_by_id(self, choice_id: UUID) -> Optional[Choice]:
        if not self.choices:
            return None
        return next((choice for choice in self.choices if choice.id == choice_id), None)

    def has_choice(self, choice_id: UUID) -> bool:
        return self.get_choice_by_id(choice_id) is not None

    def get_choices_count(self) -> int:
        return len(self.choices) if self.choices else 0

    def validate_answer_choice(self, choice_id: UUID) -> bool:
        return self.is_choice_question() and self.has_choice(choice_id)


@dataclass(frozen=True)
class Questionnaire:
    """Agregado que representa un cuestionario y sus preguntas."""

    id: UUID
    title: str
    version: str
    timezone: str
    questions: List[Question]

    def __post_init__(self) -> None:
        if not self.questions:
            raise InvariantViolationError(
                message="El cuestionario debe tener al menos una pregunta.",
                invariant_name="questionnaire_has_questions",
            )
        if not self.title.strip():
            raise ValidationError(
                message="El título del cuestionario no puede estar vacío.",
                field="title",
            )

    def get_question_by_id(self, question_id: UUID) -> Optional[Question]:
        return next((q for q in self.questions if q.id == question_id), None)

    def get_questions_by_order(self) -> List[Question]:
        return sorted(self.questions, key=lambda question: question.order)

    def has_question(self, question_id: UUID) -> bool:
        return any(question.id == question_id for question in self.questions)


@dataclass(frozen=True)
class Submission:
    """Envio de un cuestionario con su estado actual."""

    id: UUID
    questionnaire_id: UUID
    tipo_fase: str  # entrada | salida
    regulador_id: Optional[UUID] = None
    placa_vehiculo: Optional[str] = None
    finalizado: bool = False
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_cierre: Optional[datetime] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "placa_vehiculo", _normalize_str(self.placa_vehiculo))

        if self.tipo_fase not in {"entrada", "salida"}:
            raise ValidationError(
                message="El tipo de fase debe ser 'entrada' o 'salida'.",
                field="tipo_fase",
            )

        if self.finalizado and not self.fecha_cierre:
            raise InvariantViolationError(
                message="Un submission finalizado debe tener fecha de cierre.",
                invariant_name="finalized_submission_has_close_date",
            )

        if not self.finalizado and self.fecha_cierre:
            raise InvariantViolationError(
                message="Un submission no finalizado no puede tener fecha de cierre.",
                invariant_name="unfinalized_submission_no_close_date",
            )

    @classmethod
    def create_new(
        cls,
        *,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID] = None,
        placa_vehiculo: Optional[str] = None,
    ) -> "Submission":
        return cls(
            id=uuid4(),
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
        )

    def finalize(self) -> "Submission":
        if self.finalizado:
            raise BusinessRuleViolationError(
                message="El submission ya está finalizado.",
                rule_name="submission_already_finalized",
            )
        return Submission(
            id=self.id,
            questionnaire_id=self.questionnaire_id,
            tipo_fase=self.tipo_fase,
            regulador_id=self.regulador_id,
            placa_vehiculo=self.placa_vehiculo,
            finalizado=True,
            fecha_creacion=self.fecha_creacion,
            fecha_cierre=datetime.now(timezone.utc),
        )

    def is_finalized(self) -> bool:
        return self.finalizado

    def can_be_modified(self) -> bool:
        return not self.finalizado


@dataclass
class Answer:
    """Respuesta a una pregunta del cuestionario."""

    id: UUID
    submission_id: UUID
    question_id: UUID
    user_id: Optional[UUID] = None

    answer_text: Optional[str] = None
    answer_choice_id: Optional[UUID] = None
    answer_file_path: Optional[str] = None

    ocr_meta: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.answer_text = _normalize_text(self.answer_text)
        self.answer_file_path = _normalize_str(self.answer_file_path)
        self.meta = dict(self.meta or {})
        self.ocr_meta = dict(self.ocr_meta or {})

        if not self.has_content():
            raise InvariantViolationError(
                message="La respuesta debe contener texto, una opción, un archivo o metadatos.",
                invariant_name="answer_has_content",
            )

    @classmethod
    def create_new(
        cls,
        *,
        submission_id: UUID,
        question_id: UUID,
        user_id: Optional[UUID] = None,
        answer_text: Optional[str] = None,
        answer_choice_id: Optional[UUID] = None,
        answer_file_path: Optional[str] = None,
        ocr_meta: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "Answer":
        return cls(
            id=uuid4(),
            submission_id=submission_id,
            question_id=question_id,
            user_id=user_id,
            answer_text=answer_text,
            answer_choice_id=answer_choice_id,
            answer_file_path=answer_file_path,
            ocr_meta=ocr_meta or {},
            meta=meta or {},
        )

    @classmethod
    def rehydrate(
        cls,
        *,
        id: UUID,
        submission_id: UUID,
        question_id: UUID,
        user_id: Optional[UUID],
        answer_text: Optional[str],
        answer_choice_id: Optional[UUID],
        answer_file_path: Optional[str],
        ocr_meta: Dict[str, Any],
        meta: Dict[str, Any],
        timestamp: datetime,
    ) -> "Answer":
        return cls(
            id=id,
            submission_id=submission_id,
            question_id=question_id,
            user_id=user_id,
            answer_text=answer_text,
            answer_choice_id=answer_choice_id,
            answer_file_path=answer_file_path,
            ocr_meta=ocr_meta or {},
            meta=meta or {},
            timestamp=timestamp,
        )

    def update_text(self, value: Optional[str]) -> None:
        self.answer_text = _normalize_text(value)

    def update_choice(self, choice_id: Optional[UUID]) -> None:
        self.answer_choice_id = choice_id

    def update_file_path(self, path: Optional[str]) -> None:
        self.answer_file_path = _normalize_str(path)

    def set_ocr_meta(self, data: Dict[str, Any]) -> None:
        self.ocr_meta = dict(data or {})

    def set_meta(self, data: Dict[str, Any]) -> None:
        self.meta = dict(data or {})

    def with_text(self, value: Optional[str]) -> "Answer":
        return Answer(
            id=self.id,
            submission_id=self.submission_id,
            question_id=self.question_id,
            user_id=self.user_id,
            answer_text=value,
            answer_choice_id=self.answer_choice_id,
            answer_file_path=self.answer_file_path,
            ocr_meta=self.ocr_meta,
            meta=self.meta,
            timestamp=self.timestamp,
        )

    def with_choice(self, choice_id: Optional[UUID]) -> "Answer":
        return Answer(
            id=self.id,
            submission_id=self.submission_id,
            question_id=self.question_id,
            user_id=self.user_id,
            answer_text=self.answer_text,
            answer_choice_id=choice_id,
            answer_file_path=self.answer_file_path,
            ocr_meta=self.ocr_meta,
            meta=self.meta,
            timestamp=self.timestamp,
        )

    def with_file_path(self, path: Optional[str]) -> "Answer":
        return Answer(
            id=self.id,
            submission_id=self.submission_id,
            question_id=self.question_id,
            user_id=self.user_id,
            answer_text=self.answer_text,
            answer_choice_id=self.answer_choice_id,
            answer_file_path=_normalize_str(path),
            ocr_meta=self.ocr_meta,
            meta=self.meta,
            timestamp=self.timestamp,
        )

    def with_meta(self, data: Dict[str, Any]) -> "Answer":
        return Answer(
            id=self.id,
            submission_id=self.submission_id,
            question_id=self.question_id,
            user_id=self.user_id,
            answer_text=self.answer_text,
            answer_choice_id=self.answer_choice_id,
            answer_file_path=self.answer_file_path,
            ocr_meta=self.ocr_meta,
            meta=dict(data or {}),
            timestamp=self.timestamp,
        )

    def has_content(self) -> bool:
        return bool(
            self.answer_text
            or self.answer_choice_id
            or self.answer_file_path
            or (self.meta and len(self.meta) > 0)
        )

    def is_text_answer(self) -> bool:
        return bool(self.answer_text)

    def is_choice_answer(self) -> bool:
        return bool(self.answer_choice_id)

    def is_file_answer(self) -> bool:
        return bool(self.answer_file_path)

    def get_display_value(self) -> str:
        if self.answer_text:
            return self.answer_text
        if self.answer_choice_id:
            return f"Opción: {self.answer_choice_id}"
        if self.answer_file_path:
            return f"Archivo: {self.answer_file_path}"
        if self.meta:
            return "(Con metadatos)"
        return "(Sin respuesta)"


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
