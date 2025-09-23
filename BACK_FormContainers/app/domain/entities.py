from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone
from uuid import UUID, uuid4

# Excepciones específicas del dominio
from app.domain.exceptions import InvariantViolationError, ValidationError, BusinessRuleViolationError

__all__ = ["Choice", "Question", "Questionnaire", "Answer", "Submission"]


# =========================
#   Entidades de dominio
# =========================
@dataclass(frozen=True)
class Choice:
    """
    Entidad de dominio para una opción de respuesta.
    
    Representa una opción disponible para preguntas de tipo choice.
    """
    id: UUID
    text: str
    branch_to: Optional[UUID] = None  # Para lógica de ramificación condicional

    def __post_init__(self) -> None:
        """Valida invariantes después de la construcción."""
        # Normalizar texto
        object.__setattr__(self, 'text', _normalize_text(self.text) or "")
        
        # Validar invariantes
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Valida que la opción cumple con sus invariantes."""
        if not self.text.strip():
            raise ValidationError(
                message="El texto de la opción no puede estar vacío.",
                field="text"
            )

    def has_branch(self) -> bool:
        """Verifica si la opción tiene ramificación condicional."""
        return self.branch_to is not None

    def get_display_text(self) -> str:
        """Retorna el texto para mostrar al usuario."""
        return self.text


@dataclass(frozen=True)
class Question:
    """
    Entidad de dominio para una pregunta del cuestionario.
    
    Representa una pregunta individual con sus opciones y metadatos.
    """
    id: UUID
    text: str
    type: str  # "text" | "number" | "date" | "choice" | "file" | etc.
    required: bool
    order: int
    choices: Optional[List[Choice]] = None
    semantic_tag: Optional[str] = None  # "placa" | "precinto" | "contenedor" | etc.
    file_mode: Optional[str] = None     # "image_ocr", "image_dual", etc.

    def __post_init__(self) -> None:
        """Valida invariantes después de la construcción."""
        # Normalizar campos de texto
        object.__setattr__(self, 'text', _normalize_text(self.text) or "")
        object.__setattr__(self, 'semantic_tag', _normalize_str(self.semantic_tag))
        object.__setattr__(self, 'file_mode', _normalize_str(self.file_mode))
        
        # Asegurar que choices sea una lista inmutable
        if self.choices is not None:
            object.__setattr__(self, 'choices', list(self.choices))
        
        # Validar invariantes
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Valida que la pregunta cumple con sus invariantes."""
        if not self.text.strip():
            raise ValidationError(
                message="El texto de la pregunta no puede estar vacío.",
                field="text"
            )
        
        if self.type not in ["text", "number", "date", "choice", "file"]:
            raise ValidationError(
                message=f"Tipo de pregunta inválido: {self.type}",
                field="type"
            )
        
        if self.order < 0:
            raise ValidationError(
                message="El orden de la pregunta debe ser un número positivo.",
                field="order"
            )
        
        # Validar que preguntas de tipo choice tengan opciones
        if self.type == "choice" and not self.choices:
            raise ValidationError(
                message="Las preguntas de tipo 'choice' deben tener al menos una opción.",
                field="choices"
            )
        
        # Validar que preguntas que no son choice no tengan opciones
        if self.type != "choice" and self.choices:
            raise ValidationError(
                message=f"Las preguntas de tipo '{self.type}' no pueden tener opciones.",
                field="choices"
            )

    def is_choice_question(self) -> bool:
        """Verifica si es una pregunta de opción múltiple."""
        return self.type == "choice"

    def is_file_question(self) -> bool:
        """Verifica si es una pregunta de archivo."""
        return self.type == "file"

    def is_text_question(self) -> bool:
        """Verifica si es una pregunta de texto."""
        return self.type == "text"

    def is_required(self) -> bool:
        """Verifica si la pregunta es obligatoria."""
        return self.required

    def has_ocr_capability(self) -> bool:
        """Verifica si la pregunta tiene capacidad OCR."""
        return self.file_mode == "image_ocr" or self.file_mode == "image_dual"

    def get_choice_by_id(self, choice_id: UUID) -> Optional[Choice]:
        """Busca una opción por su ID."""
        if not self.choices:
            return None
        return next((choice for choice in self.choices if choice.id == choice_id), None)

    def has_choice(self, choice_id: UUID) -> bool:
        """Verifica si la pregunta contiene una opción específica."""
        return self.get_choice_by_id(choice_id) is not None

    def get_choices_count(self) -> int:
        """Retorna el número de opciones disponibles."""
        return len(self.choices) if self.choices else 0

    def validate_answer_choice(self, choice_id: UUID) -> bool:
        """Valida si un choice_id es válido para esta pregunta."""
        if not self.is_choice_question():
            return False
        return self.has_choice(choice_id)


@dataclass(frozen=True)
class Questionnaire:
    id: UUID
    title: str
    version: str
    timezone: str
    questions: List[Question]

    def __post_init__(self) -> None:
        """Valida invariantes después de la construcción."""
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Valida que el cuestionario cumple con sus invariantes."""
        if not self.questions:
            raise InvariantViolationError(
                message="El cuestionario debe tener al menos una pregunta.",
                invariant_name="questionnaire_has_questions"
            )
        
        if not self.title.strip():
            raise ValidationError(
                message="El título del cuestionario no puede estar vacío.",
                field="title"
            )

    def get_question_by_id(self, question_id: UUID) -> Optional[Question]:
        """Busca una pregunta por su ID."""
        return next((q for q in self.questions if q.id == question_id), None)

    def get_questions_by_order(self) -> List[Question]:
        """Retorna las preguntas ordenadas por su campo 'order'."""
        return sorted(self.questions, key=lambda q: q.order)

    def has_question(self, question_id: UUID) -> bool:
        """Verifica si el cuestionario contiene una pregunta específica."""
        return any(q.id == question_id for q in self.questions)


@dataclass(frozen=True)
class Submission:
    """
    Entidad de dominio para un envío de formulario.
    
    Representa una instancia de un cuestionario siendo completado por un usuario.
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
        """Valida invariantes después de la construcción."""
        # Normalizar campos de texto
        object.__setattr__(self, 'placa_vehiculo', _normalize_str(self.placa_vehiculo))
        
        # Validar invariantes
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Valida que el submission cumple con sus invariantes."""
        if self.tipo_fase not in ["entrada", "salida"]:
            raise ValidationError(
                message="El tipo de fase debe ser 'entrada' o 'salida'.",
                field="tipo_fase"
            )
        
        if self.finalizado and not self.fecha_cierre:
            raise InvariantViolationError(
                message="Un submission finalizado debe tener fecha de cierre.",
                invariant_name="finalized_submission_has_close_date"
            )
        
        if not self.finalizado and self.fecha_cierre:
            raise InvariantViolationError(
                message="Un submission no finalizado no puede tener fecha de cierre.",
                invariant_name="unfinalized_submission_no_close_date"
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
        """Crea un nuevo submission."""
        return cls(
            id=uuid4(),
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
        )

    def finalize(self) -> "Submission":
        """Retorna una nueva instancia finalizada."""
        if self.finalizado:
            raise BusinessRuleViolationError(
                message="El submission ya está finalizado.",
                rule_name="submission_already_finalized"
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
        """Verifica si el submission está finalizado."""
        return self.finalizado

    def can_be_modified(self) -> bool:
        """Verifica si el submission puede ser modificado."""
        return not self.finalizado


@dataclass(frozen=True)
class Answer:
    """
    Entidad de dominio inmutable para una respuesta a una pregunta.
    
    Invariantes:
    - Debe existir al menos UNO entre: answer_text, answer_choice_id, answer_file_path
    - Los campos de texto deben estar normalizados (sin espacios en blanco al inicio/final)
    - Los metadatos deben ser diccionarios válidos
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
        """Valida invariantes después de la construcción."""
        # Normalizar campos de texto
        object.__setattr__(self, 'answer_text', _normalize_text(self.answer_text))
        object.__setattr__(self, 'answer_file_path', _normalize_str(self.answer_file_path))
        
        # Asegurar que los metadatos sean diccionarios inmutables
        object.__setattr__(self, 'ocr_meta', dict(self.ocr_meta or {}))
        object.__setattr__(self, 'meta', dict(self.meta or {}))
        
        # Validar invariantes de dominio
        self._validate_invariants()

    # ---------------------------
    # Factory methods
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
        Crea una nueva respuesta con ID generado automáticamente.
        Garantiza que se cumplan todos los invariantes del dominio.
        """
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
        Rehidrata una respuesta desde persistencia.
        Valida invariantes pero no modifica los datos originales.
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

    # ---------------------------
    # Métodos de transformación (inmutables)
    # ---------------------------
    def with_text(self, value: Optional[str]) -> "Answer":
        """Retorna una nueva instancia con el texto actualizado."""
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
        """Retorna una nueva instancia con la opción actualizada."""
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
        """Retorna una nueva instancia con la ruta de archivo actualizada."""
        return Answer(
            id=self.id,
            submission_id=self.submission_id,
            question_id=self.question_id,
            user_id=self.user_id,
            answer_text=self.answer_text,
            answer_choice_id=self.answer_choice_id,
            answer_file_path=path,
            ocr_meta=self.ocr_meta,
            meta=self.meta,
            timestamp=self.timestamp,
        )

    def with_ocr_meta(self, data: Dict[str, Any]) -> "Answer":
        """Retorna una nueva instancia con metadatos OCR actualizados."""
        return Answer(
            id=self.id,
            submission_id=self.submission_id,
            question_id=self.question_id,
            user_id=self.user_id,
            answer_text=self.answer_text,
            answer_choice_id=self.answer_choice_id,
            answer_file_path=self.answer_file_path,
            ocr_meta=dict(data or {}),
            meta=self.meta,
            timestamp=self.timestamp,
        )

    def with_meta(self, data: Dict[str, Any]) -> "Answer":
        """Retorna una nueva instancia con metadatos actualizados."""
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

    # ---------------------------
    # Validaciones de dominio
    # ---------------------------
    def _validate_invariants(self) -> None:
        """Valida que la entidad cumple con todos sus invariantes."""
        if not self.has_content():
            raise InvariantViolationError(
                message="La respuesta debe contener texto, una opción o un archivo.",
                invariant_name="answer_has_content"
            )

    def has_content(self) -> bool:
        """Verifica si la respuesta tiene algún tipo de contenido."""
        return bool(self.answer_text or self.answer_choice_id or self.answer_file_path)

    def is_text_answer(self) -> bool:
        """Verifica si es una respuesta de texto."""
        return bool(self.answer_text)

    def is_choice_answer(self) -> bool:
        """Verifica si es una respuesta de opción múltiple."""
        return bool(self.answer_choice_id)

    def is_file_answer(self) -> bool:
        """Verifica si es una respuesta de archivo."""
        return bool(self.answer_file_path)

    def has_ocr_data(self) -> bool:
        """Verifica si tiene datos de OCR."""
        return bool(self.ocr_meta)

    # ---------------------------
    # Métodos de consulta
    # ---------------------------
    def get_display_value(self) -> str:
        """Retorna el valor de la respuesta para mostrar al usuario."""
        if self.answer_text:
            return self.answer_text
        elif self.answer_choice_id:
            return f"Opción: {self.answer_choice_id}"
        elif self.answer_file_path:
            return f"Archivo: {self.answer_file_path}"
        else:
            return "(Sin respuesta)"


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


