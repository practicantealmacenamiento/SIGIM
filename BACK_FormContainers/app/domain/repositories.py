# -*- coding: utf-8 -*-
"""
Puertos de repositorio (interfaces) para la capa de dominio.

Este módulo define contratos de persistencia para entidades núcleo:
- QuestionnaireRepository
- QuestionRepository
- ChoiceRepository
- ActorRepository
- AnswerRepository
- SubmissionRepository

Notas:
- Son Protocols/puertos: no contienen lógica, sólo contratos.
- Las implementaciones concretas (ORM, APIs externas, etc.) viven en infraestructura.
- No modificar firmas: otros módulos (servicios/casos de uso) dependen de ellas.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from typing import Optional, List, Protocol, Union
from uuid import UUID

# ── Dominio ────────────────────────────────────────────────────────────────────
from app.domain.entities import Questionnaire, Question, Answer

# ── API pública del módulo ─────────────────────────────────────────────────────
__all__ = [
    "UserPK",
    "QuestionnaireRepository",
    "QuestionRepository",
    "ChoiceRepository",
    "ActorRepository",
    "AnswerRepository",
    "SubmissionRepository",
]

# Alias para claves de usuario (flexible según origen/infraestructura)
UserPK = Union[int, UUID, str]


# ==============================================================================
#   Repositorios de lectura/escritura para el agregado Questionnaire
# ==============================================================================

class QuestionnaireRepository(Protocol):
    """Contrato mínimo para operaciones CRUD de cuestionarios."""

    def get_by_id(self, id: UUID) -> Optional[Questionnaire]:
        """Obtiene un cuestionario por su identificador (o None si no existe)."""
        ...

    def list_all(self) -> List[Questionnaire]:
        """Lista todos los cuestionarios disponibles."""
        ...

    def save(self, questionnaire: Questionnaire) -> Questionnaire:
        """Persiste (crear/actualizar) un cuestionario y retorna su estado final."""
        ...

    def delete(self, id: UUID) -> bool:
        """Elimina por id. Retorna True si se afectó un registro."""
        ...


# ==============================================================================
#   Repositorio de preguntas y navegación lineal
# ==============================================================================

class QuestionRepository(Protocol):
    """Operaciones de lectura para preguntas y utilidades de navegación."""

    def get(self, id: UUID) -> Optional[Question]:
        """Obtiene una pregunta por id (o None si no existe)."""
        ...

    def list_by_questionnaire(self, questionnaire_id: UUID) -> List[Question]:
        """Lista preguntas asociadas a un cuestionario dado."""
        ...

    # Opcionales útiles para flujo lineal
    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]:
        """Retorna el id de la siguiente pregunta en el mismo cuestionario (si existe)."""
        ...

    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[Question]:
        """Busca la siguiente pregunta con `order` inmediatamente superior."""
        ...


# ==============================================================================
#   Repositorios auxiliares (Choice, Actor)
# ==============================================================================

class ChoiceRepository(Protocol):
    """Acceso puntual a opciones de respuesta (Choice)."""

    def get(self, id: UUID):
        """Retorna la opción (objeto del modelo/DTO mínimo) o None."""
        ...


class ActorRepository(Protocol):
    """Puerto mínimo para validar/consultar actores existentes."""

    def get(self, id: UUID):
        """Obtiene un actor por id (objeto/DTO específico de infraestructura)."""
        ...

    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50):
        """
        Lista actores filtrados por `tipo` con búsqueda opcional.

        Args:
            tipo: Tipo lógico de actor (p. ej., "PROVEEDOR").
            search: Texto libre para filtrar por nombre/identificador.
            limit: Límite máximo de resultados a retornar.
        """
        ...


# ==============================================================================
#   Repositorio de respuestas (Answer)
# ==============================================================================

class AnswerRepository(Protocol):
    """
    Puerto de repositorio para respuestas (Answer).

    Incluye operaciones de limpieza/truncado usadas por el caso de uso Guardar&Avanzar.
    """

    # CRUD / Queries básicas
    def save(self, answer: Answer) -> Answer:
        """Crea/actualiza una respuesta y retorna el estado persistido."""
        ...

    def get(self, id: UUID) -> Optional[Answer]:
        """Obtiene una respuesta por id (o None si no existe)."""
        ...

    def delete(self, id: UUID) -> None:
        """Elimina una respuesta por id (idempotente)."""
        ...

    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[Answer]:
        """Lista respuestas asociadas a un usuario (opcionalmente limitado)."""
        ...

    def list_by_submission(self, submission_id: UUID) -> List[Answer]:
        """Lista todas las respuestas de un submission."""
        ...

    def list_by_question(self, question_id: UUID) -> List[Answer]:
        """Lista todas las respuestas asociadas a una pregunta (en cualquier submission)."""
        ...

    # 🔹 Nuevas utilidades (opcionales pero recomendadas para Opción B)
    def list_by_submission_question(self, *, submission_id: UUID, question_id: UUID) -> List[Answer]:
        """
        Devuelve solo las respuestas de una pregunta dentro de un submission.

        Permite optimizar el merge de múltiples proveedores sin traer todo el submission.
        Si no se implementa, la capa aplicación puede usar `list_by_submission(...)`
        y filtrar en memoria.
        """
        ...

    def save_many(self, answers: List[Answer]) -> List[Answer]:
        """
        Guarda en lote.

        La implementación puede hacer `bulk_create`/`bulk_update` o fallback a `save()` en bucle.
        La capa de aplicación puede prescindir de este método si no está disponible.
        """
        ...

    # Operaciones específicas del flujo
    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """
        Elimina respuestas de ESA pregunta dentro del submission.

        OJO: El caso de uso 'save_and_advance' NO debe llamar esto para la pregunta
        'proveedor' (multi-entrada), para evitar borrar proveedores previos.
        """
        ...

    def delete_after_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        """
        Elimina respuestas de preguntas posteriores (navegación lineal).

        Útil cuando se recontesta una pregunta intermedia y se invalida el camino
        de navegación que venía después.
        """
        ...


# ==============================================================================
#   Repositorio de submissions
# ==============================================================================

class SubmissionRepository(Protocol):
    """
    Puerto mínimo para trabajar con Submissions en los casos de uso:
      - Lectura por ID.
      - Actualizaciones parciales de campos derivados (placa, contenedor, precinto, FKs).
      - Consultas agregadas de historial.
    """

    def get(self, id: UUID):
        """Obtiene un submission (objeto/DTO específico de infraestructura)."""
        ...

    def save_partial_updates(self, id: UUID, **fields) -> None:
        """
        Persiste actualizaciones parciales (patch) de campos derivados.

        Ejemplos: `placa_vehiculo`, FKs relacionadas, datos agregados de servicio.
        """
        ...

    # Opcionales empleados por interfaces (list/detail/history)
    def list_for_api(self, params, *, user=None, include_all: bool = False):
        """Query/listado adaptable para vistas de API (filtros/paginación desde params)."""
        ...

    def ensure_regulador_on_create(self, obj) -> None:
        """Hook para asegurar consistencia de `regulador` al crear (si aplica)."""
        ...

    def detail_queryset(self, *, user=None, include_all: bool = False):
        """Devuelve un queryset/base de detalle optimizado (select_related/prefetch)."""
        ...

    def get_detail(self, id: UUID, *, user=None, include_all: bool = False):
        """Obtiene el detalle de un submission (proyección enriquecida)."""
        ...

    def history_aggregate(self, *, fecha_desde=None, fecha_hasta=None, user=None, include_all: bool = False):
        """Agregaciones para módulo de historial (rango de fechas opcional)."""
        ...

    def get_by_ids(self, ids, *, user=None, include_all: bool = False):
        """Obtiene múltiples submissions por sus identificadores (para listados/exports)."""
        ...
