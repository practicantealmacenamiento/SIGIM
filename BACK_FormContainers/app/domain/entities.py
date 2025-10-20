# -*- coding: utf-8 -*-
"""
Entidades de dominio del módulo de Cuestionarios.

Este archivo define las *entidades puras* que modelan el núcleo del dominio:
- Choice: opción de respuesta para preguntas de tipo "choice".
- Question: pregunta del cuestionario (texto, número, fecha, choice, archivo).
- Questionnaire: agregado que contiene preguntas y metadatos.
- Submission: envío de formulario (estado de finalización, fechas, etc.).
- Answer: respuesta a una pregunta (texto, opción, archivo y metadatos).

Importante:
- Estas entidades no dependen de frameworks ni del ORM. Son *agnósticas*.
- No modificar firmas ni comportamiento: otros módulos (servicios/repositorios)
  dependen de su API pública.
- Las validaciones aquí son *invariantes del dominio* (no de UI ni de infraestructura).

Convenciones:
- Campos inmutables se anotan con `@dataclass(frozen=True)` cuando aplica.
- Normalizamos strings con utilidades locales `_normalize_text` y `_normalize_str`.
- Fechas en UTC (`datetime.now(timezone.utc)`).

"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

# ── Dominio ────────────────────────────────────────────────────────────────────
# Excepciones específicas del dominio
from app.domain.exceptions import (
    InvariantViolationError,
    ValidationError,
    BusinessRuleViolationError,
)

__all__ = ["Choice", "Question", "Questionnaire", "Answer", "Submission"]


# ==============================================================================
#   Entidades de dominio
# ==============================================================================

@dataclass(frozen=True)
class Choice:
    """
    Opción de respuesta para una pregunta tipo "choice".

    Attributes:
        id: Identificador único de la opción.
        text: Texto visible de la opción (se normaliza y no puede ser vacío).
        branch_to: Si está presente, indica la pregunta a la que se ramifica.
    """
    id: UUID
    text: str
    branch_to: Optional[UUID] = None  # Para lógica de ramificación condicional

    def __post_init__(self) -> None:
        # Normalización y validación de invariantes
        object.__setattr__(self, "text", _normalize_text(self.text) or "")
        if not self.text.strip():
            raise ValidationError(message="El texto de la opción no puede estar vacío.", field="text")

    def has_branch(self) -> bool:
        """Indica si la opción define una ramificación."""
        return self.branch_to is not None

    def get_display_text(self) -> str:
        """Retorna el texto visible de la opción."""
        return self.text


@dataclass(frozen=True)
class Question:
    """
    Pregunta del cuestionario.
    (Sin campos tabulares en UI de admin; lo tabular vive en Answer)

    Attributes:
        id: Identificador de la pregunta.
        text: Enunciado (se normaliza y no puede ser vacío).
        type: Tipo de dato ("text" | "number" | "date" | "choice" | "file").
        required: Si la respuesta es obligatoria.
        order: Posición relativa dentro del cuestionario (>= 0).
        choices: Opciones disponibles cuando type == "choice".
        semantic_tag: Etiqueta semántica (p.ej. "PROVEEDOR").
        file_mode: Modalidad para archivos (p.ej. "image_ocr", "image_dual").
    """
    id: UUID
    text: str
    type: str  # "text" | "number" | "date" | "choice" | "file" | etc.
    required: bool
    order: int
    choices: Optional[List[Choice]] = None
    semantic_tag: Optional[str] = None  # "PROVEEDOR" | "placa" | ...
    file_mode: Optional[str] = None     # "image_ocr", "image_dual", etc.

    def __post_init__(self) -> None:
        # Normalización defensiva
        object.__setattr__(self, "text", _normalize_text(self.text) or "")
        object.__setattr__(self, "semantic_tag", _normalize_str(self.semantic_tag))
        object.__setattr__(self, "file_mode", _normalize_str(self.file_mode))
        if self.choices is not None:
            # Congelar la lista de opciones en el estado actual (no mutamos referencias externas)
            object.__setattr__(self, "choices", list(self.choices))
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Valida invariantes de la entidad Question."""
        if not self.text.strip():
            raise ValidationError(message="El texto de la pregunta no puede estar vacío.", field="text")

        if self.type not in ["text", "number", "date", "choice", "file"]:
            raise ValidationError(message=f"Tipo de pregunta inválido: {self.type}", field="type")

        if self.order < 0:
            raise ValidationError(message="El orden de la pregunta debe ser un número positivo.", field="order")

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

    # Helpers semánticos (no alteran estado)
    def is_choice_question(self) -> bool: return self.type == "choice"
    def is_file_question(self) -> bool: return self.type == "file"
    def is_text_question(self) -> bool: return self.type == "text"
    def is_required(self) -> bool: return self.required
    def has_ocr_capability(self) -> bool: return self.file_mode in {"image_ocr", "image_dual"}

    def is_proveedor(self) -> bool:
        """Indica si la pregunta pertenece al grupo semántico de proveedor(es)."""
        tag = (self.semantic_tag or "").strip().upper()
        return tag in {"PROVEEDOR", "PROVEEDORES"}

    def get_choice_by_id(self, choice_id: UUID) -> Optional[Choice]:
        """Busca una opción por id cuando la pregunta es de tipo 'choice'."""
        if not self.choices:
            return None
        return next((choice for choice in self.choices if choice.id == choice_id), None)

    def has_choice(self, choice_id: UUID) -> bool:
        """True si la opción existe en esta pregunta."""
        return self.get_choice_by_id(choice_id) is not None

    def get_choices_count(self) -> int:
        """Cantidad de opciones (0 si no aplica)."""
        return len(self.choices) if self.choices else 0

    def validate_answer_choice(self, choice_id: UUID) -> bool:
        """Valida que `choice_id` pertenezca a esta pregunta y que sea de tipo 'choice'."""
        return self.is_choice_question() and self.has_choice(choice_id)


@dataclass(frozen=True)
class Questionnaire:
    """
    Agregado que representa un cuestionario.

    Attributes:
        id: Identificador del cuestionario.
        title: Título (no vacío).
        version: Versión legible del cuestionario.
        timezone: Zona horaria de referencia.
        questions: Colección de preguntas (no vacía).
    """
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
            raise ValidationError(message="El título del cuestionario no puede estar vacío.", field="title")

    def get_question_by_id(self, question_id: UUID) -> Optional[Question]:
        """Obtiene una pregunta por su id."""
        return next((q for q in self.questions if q.id == question_id), None)

    def get_questions_by_order(self) -> List[Question]:
        """Retorna las preguntas ordenadas por el campo `order` ascendente."""
        return sorted(self.questions, key=lambda q: q.order)

    def has_question(self, question_id: UUID) -> bool:
        """True si la pregunta existe en el cuestionario."""
        return any(q.id == question_id for q in self.questions)


@dataclass(frozen=True)
class Submission:
    """
    Envío de formulario.

    Attributes:
        id: Identificador del envío.
        questionnaire_id: Referencia al cuestionario.
        tipo_fase: "entrada" | "salida".
        regulador_id: Identificador del regulador (si aplica).
        placa_vehiculo: Placa normalizada (opcional).
        finalizado: Estado del envío.
        fecha_creacion: Fecha/hora (UTC) de creación.
        fecha_cierre: Fecha/hora (UTC) de cierre, sólo si `finalizado=True`.
    """
    id: UUID
    questionnaire_id: UUID
    tipo_fase: str  # "entrada" | "salida"
    regulador_id: Optional[UUID] = None
    placa_vehiculo: Optional[str] = None
    finalizado: bool = False
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_cierre: Optional[datetime] = None

    def __post_init__(self) -> None:
        # Normalización básica
        object.__setattr__(self, "placa_vehiculo", _normalize_str(self.placa_vehiculo))

        # Invariantes de consistencia temporal/estado
        if self.tipo_fase not in ["entrada", "salida"]:
            raise ValidationError(message="El tipo de fase debe ser 'entrada' o 'salida'.", field="tipo_fase")

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
        """Fábrica para crear un envío nuevo con `id` y `fecha_creacion` por defecto."""
        return cls(
            id=uuid4(),
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
        )

    def finalize(self) -> "Submission":
        """
        Devuelve una *nueva* instancia marcada como finalizada y con `fecha_cierre` en UTC.
        No muta la instancia actual (entidad inmutable).
        """
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
        """True si el envío está finalizado."""
        return self.finalizado

    def can_be_modified(self) -> bool:
        """True si el envío admite modificaciones (no finalizado)."""
        return not self.finalizado


@dataclass
class Answer:
    """
    Respuesta a una pregunta.

    Esquema clásico (compatibilidad con infraestructura/servicios existentes):
      - user_id opcional (auditoría)
      - answer_file_path como referencia al archivo almacenado
      - ocr_meta y meta como diccionarios
      - timestamp en UTC
    """
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
        # Normalización defensiva
        self.answer_text = _normalize_text(self.answer_text)
        self.answer_file_path = _normalize_str(self.answer_file_path)
        self.meta = dict(self.meta or {})
        self.ocr_meta = dict(self.ocr_meta or {})

        # Invariante: debe haber contenido en alguno de los canales
        if not self.has_content():
            raise InvariantViolationError(
                message="La respuesta debe contener texto, una opción, un archivo o metadatos.",
                invariant_name="answer_has_content",
            )

    # ── Fábricas ───────────────────────────────────────────────────────────────
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
        """Crea una respuesta nueva con `id` y `timestamp` por defecto."""
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
        """
        Reconstruye una instancia completa (p.ej. desde persistencia),
        respetando el `timestamp` original.
        """
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

    # ── Mutadores (usados por servicios) ───────────────────────────────────────
    def update_text(self, value: Optional[str]) -> None:
        """Actualiza el texto normalizándolo."""
        self.answer_text = _normalize_text(value)

    def update_choice(self, choice_id: Optional[UUID]) -> None:
        """Selecciona/cambia la opción elegida."""
        self.answer_choice_id = choice_id

    def update_file_path(self, path: Optional[str]) -> None:
        """Actualiza la ruta del archivo normalizándola."""
        self.answer_file_path = _normalize_str(path)

    def set_ocr_meta(self, data: Dict[str, Any]) -> None:
        """Reemplaza por completo los metadatos OCR."""
        self.ocr_meta = dict(data or {})

    def set_meta(self, data: Dict[str, Any]) -> None:
        """Reemplaza por completo los metadatos adicionales."""
        self.meta = dict(data or {})

    # ── Estilo inmutable (compatibilidad con call sites existentes) ────────────
    def with_text(self, value: Optional[str]) -> "Answer":
        """Copia con nuevo `answer_text` (no muta la instancia actual)."""
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
        """Copia con nuevo `answer_choice_id`."""
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
        """Copia con nueva `answer_file_path` normalizada."""
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
        """Copia con nuevos `meta` (reemplazo completo)."""
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

    # ── Consultas/derivados ────────────────────────────────────────────────────
    def has_content(self) -> bool:
        """
        True si la respuesta contiene información útil en cualquiera de sus canales:
        texto, opción elegida, archivo o metadatos adicionales.
        """
        return bool(
            self.answer_text
            or self.answer_choice_id
            or self.answer_file_path
            or (self.meta and len(self.meta) > 0)
        )

    def is_text_answer(self) -> bool: return bool(self.answer_text)
    def is_choice_answer(self) -> bool: return bool(self.answer_choice_id)
    def is_file_answer(self) -> bool: return bool(self.answer_file_path)

    def get_display_value(self) -> str:
        """
        Representación legible resumida del valor de la respuesta.
        Útil para listados simples en UI/logs.
        """
        if self.answer_text:
            return self.answer_text
        elif self.answer_choice_id:
            return f"Opción: {self.answer_choice_id}"
        elif self.answer_file_path:
            return f"Archivo: {self.answer_file_path}"
        elif self.meta:
            return "(Con metadatos)"
        else:
            return "(Sin respuesta)"


# ==============================================================================
#   Utilidades locales
# ==============================================================================

def _normalize_text(value: Optional[str]) -> Optional[str]:
    """
    Normaliza un texto:
      - None -> None
      - str -> `str(value).strip()` y retorna None si queda vacío.
    """
    if value is None:
        return None
    t = str(value).strip()
    return t if t else None


def _normalize_str(value: Optional[str]) -> Optional[str]:
    """
    Normaliza una cadena genérica (ruta, etiqueta, etc.):
      - None -> None
      - str -> `str(value).strip()` y retorna None si queda vacío.
    """
    if value is None:
        return None
    t = str(value).strip()
    return t if t else None
