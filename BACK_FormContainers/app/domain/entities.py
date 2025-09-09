from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone
from uuid import UUID, uuid4

# Excepciones de la capa aplicación usadas por el dominio
from app.application.exceptions import ValidationError

__all__ = ["Choice", "Question", "Questionnaire", "Answer"]


# =========================
#   Entidades de dominio
# =========================
@dataclass(frozen=True)
class Choice:
    id: UUID
    text: str
    # Ramificación opcional (si aplica en tu flujo)
    branch_to: Optional[UUID] = None


@dataclass(frozen=True)
class Question:
    id: UUID
    text: str
    type: str                # "text" | "number" | "date" | "choice" | "file" | ...
    required: bool
    order: int
    choices: Optional[List[Choice]] = None
    # Metadatos que tu UI/back ya usan:
    semantic_tag: Optional[str] = None     # p.ej. "placa" | "precinto" | "contenedor" | "proveedor" | ...
    file_mode: Optional[str] = None        # p.ej. "image_ocr", "image_dual", etc.


@dataclass(frozen=True)
class Questionnaire:
    id: UUID
    title: str
    version: str
    timezone: str
    questions: List[Question]


@dataclass
class Answer:
    """
    Entidad de dominio para una respuesta a una pregunta.
    Invariante: Debe existir al menos UNO entre:
      - answer_text
      - answer_choice_id
      - answer_file_path
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

    # ---------------------------
    # Factories (creación/rehidr)
    # ---------------------------
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
        """
        Crea una nueva respuesta garantizando los invariantes.
        (Usada por QuestionnaireService.save_and_advance)
        """
        entity = cls(
            id=uuid4(),
            submission_id=submission_id,
            question_id=question_id,
            user_id=user_id,
            answer_text=_normalize_text(answer_text),
            answer_choice_id=answer_choice_id,
            answer_file_path=_normalize_str(answer_file_path),
            ocr_meta=dict(ocr_meta or {}),
            meta=dict(meta or {}),
        )
        entity._validate_invariants()
        return entity

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
        Rehidrata desde persistencia. No cambia campos ni normaliza (salvo trims),
        pero sí valida invariantes.
        """
        entity = cls(
            id=id,
            submission_id=submission_id,
            question_id=question_id,
            user_id=user_id,
            answer_text=_normalize_text(answer_text),
            answer_choice_id=answer_choice_id,
            answer_file_path=_normalize_str(answer_file_path),
            ocr_meta=dict(ocr_meta or {}),
            meta=dict(meta or {}),
            timestamp=timestamp,
        )
        entity._validate_invariants()
        return entity

    # ---------------------------
    # Mutadores controlados
    # ---------------------------
    def update_text(self, value: Optional[str]) -> None:
        self.answer_text = _normalize_text(value)
        self._validate_invariants()

    def update_choice(self, choice_id: Optional[UUID]) -> None:
        self.answer_choice_id = choice_id
        self._validate_invariants()

    def update_file_path(self, path: Optional[str]) -> None:
        self.answer_file_path = _normalize_str(path)
        self._validate_invariants()

    def set_ocr_meta(self, data: Optional[Dict[str, Any]]) -> None:
        self.ocr_meta = dict(data or {})

    def set_meta(self, data: Optional[Dict[str, Any]]) -> None:
        self.meta = dict(data or {})

    # ---------------------------
    # Reglas/Invariantes
    # ---------------------------
    def _validate_invariants(self) -> None:
        if not (self.answer_text or self.answer_choice_id or self.answer_file_path):
            raise ValidationError("La respuesta debe contener texto, una opción o un archivo.")

    # ---------------------------
    # Serialización personalizada
    # ---------------------------
    def as_dict(self) -> dict:
        question = getattr(self, "question", None)

        return {
            "id": str(self.id),
            "submission_id": str(self.submission_id),
            "question_id": str(self.question_id),
            "question_text": getattr(question, "text", "(Pregunta eliminada)"),
            "question_type": getattr(question, "type", None),
            "question_tag": getattr(question, "semantic_tag", None),
            "answer_text": self.answer_text,
            "answer_choice_id": str(self.answer_choice_id) if self.answer_choice_id else None,
            "answer_file_path": self.answer_file_path,
            "ocr_meta": self.ocr_meta,
            "meta": self.meta,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =========================
#   Utilidades locales
# =========================
def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    t = str(value).strip()
    return t if t else None

def _normalize_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    t = str(value).strip()
    return t if t else None


