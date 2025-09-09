from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, List
from uuid import UUID

# Sentinel para diferenciar "no enviado" de "None"
UNSET = object()


@dataclass(frozen=True)
class CreateAnswerCommand:
    submission_id: UUID
    question_id: UUID
    user_id: Optional[UUID] = None

    answer_text: Optional[str] = None
    answer_choice_id: Optional[UUID] = None
    upload: Optional[Any] = None  # UploadedFile/Django File-like

    # Si algún caso de uso debe permitir setearlos:
    ocr_meta: Optional[dict] = None
    meta: Optional[dict] = None


@dataclass(frozen=True)
class UpdateAnswerCommand:
    id: UUID

    # Campos parciales: UNSET = no tocar; None = limpiar; valor = asignar
    answer_text: Any = field(default=UNSET)
    answer_choice_id: Any = field(default=UNSET)
    upload: Any = field(default=UNSET)  # UploadedFile | None | UNSET

    # Actualización de metadatos (opcional)
    ocr_meta: Any = field(default=UNSET)
    meta: Any = field(default=UNSET)

    # Si reemplazas archivo, ¿eliminar el anterior del storage?
    delete_old_file_on_replace: bool = True


@dataclass(frozen=True)
class SaveAndAdvanceCommand:
    """
    Command principal del flujo de cuestionario.
    - Al menos uno de: answer_text, answer_choice_id, uploads debe venir.
    - `uploads`: lista de 0..2 archivos (en preguntas sin OCR).
    """
    submission_id: UUID
    question_id: UUID
    user_id: Optional[UUID] = None

    answer_text: Optional[str] = None
    answer_choice_id: Optional[UUID] = None
    uploads: List[Any] = field(default_factory=list)  # UploadedFile-like

    # Bandera para truncar futuras respuestas (default True, como en tus views)
    force_truncate_future: bool = True


@dataclass(frozen=True)
class SaveAndAdvanceResult:
    """
    Resultado del caso de uso Guardar y Avanzar.
    """
    saved_answer: Any  # entidad de dominio Answer
    next_question_id: Optional[UUID]
    is_finished: bool
    derived_updates: dict
    warnings: List[str] = field(default_factory=list)
