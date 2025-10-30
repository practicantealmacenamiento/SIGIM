"""Puertos (interfaces) para persistencia utilizada en el dominio."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union
from uuid import UUID

from app.domain.entities import Answer, Choice, Question, Questionnaire, Submission

UserPK = Union[UUID, int, str]

__all__ = [
    "UserPK",
    "AnswerRepository",
    "SubmissionRepository",
    "QuestionRepository",
    "ChoiceRepository",
    "QuestionnaireRepository",
    "ActorRepository",
]


# ---------------------------------------------------------------------------
# Respuestas
# ---------------------------------------------------------------------------


class AnswerRepository(ABC):
    """Contrato de persistencia para entidades Answer."""

    @abstractmethod
    def save(self, answer: Answer) -> Answer:
        """Crea o actualiza una respuesta."""

    @abstractmethod
    def save_many(self, answers: Sequence[Answer]) -> List[Answer]:
        """Persiste múltiples respuestas y retorna las almacenadas."""

    @abstractmethod
    def get(self, id: UUID) -> Optional[Answer]:
        """Obtiene una respuesta por su identificador."""

    @abstractmethod
    def delete(self, id: UUID) -> None:
        """Elimina una respuesta si existe."""

    @abstractmethod
    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[Answer]:
        """Lista respuestas recientes asociadas a un usuario."""

    @abstractmethod
    def list_by_submission(self, submission_id: UUID) -> List[Answer]:
        """Lista respuestas de un submission."""

    @abstractmethod
    def list_by_question(self, question_id: UUID) -> List[Answer]:
        """Lista respuestas de una pregunta."""

    @abstractmethod
    def list_by_submission_question(self, *, submission_id: UUID, question_id: UUID) -> List[Answer]:
        """Lista respuestas para el par submission/pregunta."""

    @abstractmethod
    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """Elimina respuestas de una pregunta dentro del submission."""

    @abstractmethod
    def delete_after_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """Elimina respuestas posteriores a la pregunta dada."""


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


class SubmissionRepository(ABC):
    """Contrato de persistencia para envíos (Submission)."""

    @abstractmethod
    def get(self, id: UUID) -> Optional[Submission]:
        """Obtiene un submission por id."""

    @abstractmethod
    def save(self, submission: Submission) -> Submission:
        """Crea o actualiza la entidad."""

    @abstractmethod
    def save_partial_updates(self, id: UUID, **fields: Any) -> None:
        """Actualiza campos puntuales de un submission existente."""

    @abstractmethod
    def find_recent_draft_without_answers(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID],
        minutes: int = 10,
    ) -> Optional[Submission]:
        """Busca borradores recientes sin respuestas."""

    @abstractmethod
    def create_submission(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID] = None,
        placa_vehiculo: Optional[str] = None,
        created_by: Any = None,
    ) -> Submission:
        """Crea un submission nuevo y lo devuelve."""

    @abstractmethod
    def get_fase1_by_regulador(self, regulador_id: UUID) -> Optional[Submission]:
        """Obtiene el último submission de fase 1 para un regulador."""

    @abstractmethod
    def set_regulador(self, submission_id: UUID, regulador_id: UUID) -> None:
        """Asigna o actualiza el regulador asociado."""

    @abstractmethod
    def list_for_api(self, params: Dict[str, Any], *, user: Any = None, include_all: bool = False) -> Any:
        """Devuelve un objeto iterable apto para la capa API."""

    @abstractmethod
    def get_for_api(self, id: UUID, *, user: Any = None, include_all: bool = False) -> Any:
        """Devuelve un objeto apto para serialización directa."""

    @abstractmethod
    def detail_queryset(self, *, user: Any = None, include_all: bool = False) -> Any:
        """Retorna un queryset preparado para vistas de detalle."""

    @abstractmethod
    def get_detail(self, id: UUID, *, user: Any = None, include_all: bool = False) -> Optional[Submission]:
        """Devuelve un submission con la información relacionado necesaria."""

    @abstractmethod
    def history_aggregate(
        self,
        *,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        user: Any = None,
        include_all: bool = False,
    ) -> Iterable[Dict[str, Any]]:
        """Agrega el historial por regulador."""

    @abstractmethod
    def get_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        user: Any = None,
        include_all: bool = False,
    ) -> Dict[str, Any]:
        """Devuelve un diccionario id->submission-like."""


# ---------------------------------------------------------------------------
# Preguntas y opciones
# ---------------------------------------------------------------------------


class QuestionRepository(ABC):
    """Contrato para persistir preguntas."""

    @abstractmethod
    def get(self, id: UUID) -> Optional[Question]:
        """Obtiene una pregunta por id."""

    @abstractmethod
    def list_by_questionnaire(self, questionnaire_id: UUID) -> List[Question]:
        """Lista preguntas asociadas a un cuestionario."""

    @abstractmethod
    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]:
        """Retorna el id de la pregunta siguiente dentro del cuestionario."""

    @abstractmethod
    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[Question]:
        """Encuentra la siguiente pregunta según el orden indicado."""

    def list_by_ids(self, ids: Iterable[UUID]) -> List[Question]:
        """Helper opcional para obtener preguntas en lote."""
        raise NotImplementedError

    def get_by_id(self, id: str) -> Any:
        """Helper opcional para exponer acceso de bajo nivel."""
        raise NotImplementedError


class ChoiceRepository(ABC):
    """Contrato para persistir opciones (Choice)."""

    @abstractmethod
    def get(self, id: UUID) -> Optional[Choice]:
        """Obtiene una opción por id."""


# ---------------------------------------------------------------------------
# Cuestionarios
# ---------------------------------------------------------------------------


class QuestionnaireRepository(ABC):
    """Contrato de persistencia para cuestionarios."""

    @abstractmethod
    def list_all(self) -> List[Questionnaire]:
        """Lista todos los cuestionarios con preguntas cargadas."""

    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[Questionnaire]:
        """Obtiene un cuestionario por id."""

    @abstractmethod
    def save(self, questionnaire: Questionnaire) -> Questionnaire:
        """Crea o actualiza el agregado de cuestionario."""

    @abstractmethod
    def list_minimal(self) -> Any:
        """Listado ligero para selectores o combos."""

    @abstractmethod
    def delete(self, id: UUID) -> bool:
        """Elimina un cuestionario y devuelve si hubo cambios."""


# ---------------------------------------------------------------------------
# Actores
# ---------------------------------------------------------------------------


class ActorRepository(ABC):
    """Contrato para catálogos de actores (proveedores, etc.)."""

    @abstractmethod
    def get(self, id: Any) -> Any:
        """Obtiene un actor por id."""

    @abstractmethod
    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50) -> List[Any]:
        """Lista actores filtrados por tipo."""

    @abstractmethod
    def public_list(self, params: Dict[str, Any]) -> Any:
        """Devuelve un iterable o queryset para listados públicos."""

    @abstractmethod
    def admin_queryset(self, params: Dict[str, Any]) -> Any:
        """Devuelve un iterable o queryset orientado a backoffice."""
