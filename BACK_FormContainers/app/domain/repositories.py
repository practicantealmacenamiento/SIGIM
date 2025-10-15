from __future__ import annotations
from typing import Optional, List, Protocol, Union
from uuid import UUID

# Entidades de dominio
from app.domain.entities import Questionnaire, Question, Answer

UserPK = Union[int, UUID, str]


class QuestionnaireRepository(Protocol):
    def get_by_id(self, id: UUID) -> Optional[Questionnaire]: ...
    def list_all(self) -> List[Questionnaire]: ...
    def save(self, questionnaire: Questionnaire) -> Questionnaire: ...
    def delete(self, id: UUID) -> bool: ...


class QuestionRepository(Protocol):
    def get(self, id: UUID) -> Optional[Question]: ...
    def list_by_questionnaire(self, questionnaire_id: UUID) -> List[Question]: ...

    # Opcionales útiles para flujo lineal
    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]: ...
    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[Question]: ...


class ChoiceRepository(Protocol):
    def get(self, id: UUID):
        """Retorna la opción (objeto del modelo/DTO mínimo) o None."""
        ...


class ActorRepository(Protocol):
    """Puerto mínimo para validar/consultar actores existentes."""
    def get(self, id: UUID): ...
    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50): ...


class AnswerRepository(Protocol):
    """
    Puerto de repositorio para respuestas (Answer).
    Incluye operaciones de limpieza/truncado usadas por el caso de uso Guardar&Avanzar.
    """

    # CRUD / Queries básicas
    def save(self, answer: Answer) -> Answer: ...
    def get(self, id: UUID) -> Optional[Answer]: ...
    def delete(self, id: UUID) -> None: ...
    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[Answer]: ...
    def list_by_submission(self, submission_id: UUID) -> List[Answer]: ...
    def list_by_question(self, question_id: UUID) -> List[Answer]: ...

    # 🔹 Nuevas utilidades (opcionales pero recomendadas para Opción B)
    def list_by_submission_question(self, *, submission_id: UUID, question_id: UUID) -> List[Answer]: ...
    """Devuelve solo las respuestas de una pregunta dentro de un submission.
    Permite optimizar el merge de múltiples proveedores sin traer todo el submission.
    Si no se implementa, la capa aplicación puede usar list_by_submission(...) y filtrar en memoria.
    """

    def save_many(self, answers: List[Answer]) -> List[Answer]: ...
    """Guarda en lote. La implementación puede hacer bulk_create/bulk_update o fallback a save() en bucle.
    La capa de aplicación puede prescindir de este método si no está disponible.
    """

    # Operaciones específicas del flujo
    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int: ...
    """Elimina respuestas de ESA pregunta dentro del submission.
    OJO: El caso de uso 'save_and_advance' NO debe llamar esto para la pregunta 'proveedor'.
    """

    def delete_after_question(self, *, submission_id: UUID, question_id: UUID) -> int: ...
    """Elimina respuestas de preguntas posteriores (navegación lineal).
    """


class SubmissionRepository(Protocol):
    """
    Puerto mínimo para trabajar con Submissions en los casos de uso:
      - Lectura por ID
      - Actualizaciones parciales de campos derivados (placa, contenedor, precinto, FKs)
      - Consultas agregadas de historial
    """

    def get(self, id: UUID):
        ...

    def save_partial_updates(self, id: UUID, **fields) -> None:
        ...

    # Opcionales empleados por interfaces (list/detail/history)
    def list_for_api(self, params): ...
    def ensure_regulador_on_create(self, obj) -> None: ...
    def detail_queryset(self): ...
    def get_detail(self, id: UUID): ...
    def history_aggregate(self, *, fecha_desde=None, fecha_hasta=None): ...
    def get_by_ids(self, ids): ...


__all__ = [
    "UserPK",
    "QuestionnaireRepository",
    "QuestionRepository",
    "ChoiceRepository",
    "AnswerRepository",
    "SubmissionRepository",
]
