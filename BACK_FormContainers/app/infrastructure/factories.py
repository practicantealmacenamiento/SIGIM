# -*- coding: utf-8 -*-
"""
Fábrica de servicios para inyección de dependencias.

Este módulo implementa el patrón Factory para centralizar la creación y
configuración de los servicios de aplicación junto con sus dependencias.

Principios (Clean Architecture):
- Las dependencias apuntan hacia el dominio.
- Las implementaciones de infraestructura se inyectan en servicios de aplicación.
- Los servicios dependen únicamente de interfaces del dominio (puertos y repositorios).

Uso típico:
    factory = get_service_factory()
    answer_service = factory.create_answer_service()
    submission_service = factory.create_submission_service()
"""

from __future__ import annotations

from typing import Optional

# ── Puertos / Repositorios del dominio ─────────────────────────────────────────
from app.domain.ports import FileStorage, NotificationServicePort, TextExtractorPort
from app.domain.repositories import ActorRepository

# ── Implementaciones de infraestructura ────────────────────────────────────────
from app.infrastructure.repositories import (
    DjangoAnswerRepository,
    DjangoSubmissionRepository,
    DjangoQuestionRepository,
    DjangoChoiceRepository,
    DjangoQuestionnaireRepository,
    DjangoActorRepository,
)
from app.infrastructure.storage import DjangoDefaultStorageAdapter
from app.infrastructure.vision_adapter import TextExtractorAdapter

__all__ = [
    "ServiceFactory",
    "get_service_factory",
    "reset_service_factory",
]


class ServiceFactory:
    """
    Fábrica para crear servicios de aplicación con inyección de dependencias.

    Centraliza la construcción de servicios y garantiza que las dependencias
    se inyecten respetando el principio de inversión de dependencias.
    """

    def __init__(self):
        """Inicializa la fábrica con configuración por defecto (lazy)."""
        self._answer_repo = None
        self._submission_repo = None
        self._question_repo = None
        self._choice_repo = None
        self._questionnaire_repo = None
        self._file_storage: Optional[FileStorage] = None
        self._text_extractor: Optional[TextExtractorPort] = None
        self._notification_service: Optional[NotificationServicePort] = None
        self._actor_repo: Optional[ActorRepository] = None

    # ==========================================================================
    #   Repositorios (inicialización diferida)
    # ==========================================================================

    def _get_actor_repository(self) -> ActorRepository:
        if self._actor_repo is None:
            self._actor_repo = DjangoActorRepository()
        return self._actor_repo

    def _get_answer_repository(self):
        """Obtiene o crea la instancia del repositorio de Answer."""
        if self._answer_repo is None:
            self._answer_repo = DjangoAnswerRepository()
        return self._answer_repo

    def _get_submission_repository(self):
        """Obtiene o crea la instancia del repositorio de Submission."""
        if self._submission_repo is None:
            self._submission_repo = DjangoSubmissionRepository()
        return self._submission_repo

    def _get_question_repository(self):
        """Obtiene o crea la instancia del repositorio de Question."""
        if self._question_repo is None:
            self._question_repo = DjangoQuestionRepository()
        return self._question_repo

    def _get_choice_repository(self):
        """Obtiene o crea la instancia del repositorio de Choice."""
        if self._choice_repo is None:
            self._choice_repo = DjangoChoiceRepository()
        return self._choice_repo

    def _get_questionnaire_repository(self):
        """Obtiene o crea la instancia del repositorio de Questionnaire."""
        if self._questionnaire_repo is None:
            self._questionnaire_repo = DjangoQuestionnaireRepository()
        return self._questionnaire_repo

    # ==========================================================================
    #   Puertos (implementaciones de infraestructura)
    # ==========================================================================

    def _get_file_storage(self) -> FileStorage:
        """Obtiene o crea la implementación del puerto FileStorage."""
        if self._file_storage is None:
            self._file_storage = DjangoDefaultStorageAdapter()
        return self._file_storage

    def _get_text_extractor(self) -> TextExtractorPort:
        """Obtiene o crea la implementación del puerto TextExtractor."""
        if self._text_extractor is None:
            self._text_extractor = TextExtractorAdapter(
                mode="text",
                language_hints=["es", "en"],
            )
        return self._text_extractor

    def _get_notification_service(self) -> Optional[NotificationServicePort]:
        """Obtiene la implementación del puerto de notificaciones (si existe)."""
        # TODO: Implementar adaptador cuando sea necesario.
        return self._notification_service

    # ==========================================================================
    #   Servicios de aplicación
    # ==========================================================================

    def create_answer_service(self):
        """
        Crea AnswerService con sus dependencias.

        Returns:
            AnswerService: instancia configurada.
        """
        from app.application.services import AnswerService
        return AnswerService(
            repo=self._get_answer_repository(),
            storage=self._get_file_storage(),
        )

    def create_submission_service(self):
        """
        Crea SubmissionService con sus dependencias.

        Returns:
            SubmissionService: instancia configurada.
        """
        from app.application.services import SubmissionService
        return SubmissionService(
            submission_repo=self._get_submission_repository(),
            answer_repo=self._get_answer_repository(),
            question_repo=self._get_question_repository(),
        )

    def create_questionnaire_service(self):
        """
        Crea QuestionnaireService con sus dependencias.

        Returns:
            QuestionnaireService: instancia configurada.
        """
        from app.application.questionnaire import QuestionnaireService
        return QuestionnaireService(
            answer_repo=self._get_answer_repository(),
            submission_repo=self._get_submission_repository(),
            question_repo=self._get_question_repository(),
            choice_repo=self._get_choice_repository(),
            storage=self._get_file_storage(),
        )

    def create_history_service(self):
        """
        Crea HistoryService con sus dependencias.

        Returns:
            HistoryService: instancia configurada.
        """
        from app.application.services import HistoryService
        return HistoryService(
            submission_repo=self._get_submission_repository(),
            answer_repo=self._get_answer_repository(),
            question_repo=self._get_question_repository(),
        )

    def create_verification_service(self):
        """
        Crea VerificationService con sus dependencias.

        Returns:
            VerificationService: instancia configurada.
        """
        from app.application.verification import VerificationService
        return VerificationService(
            text_extractor=self._get_text_extractor(),
            question_repo=self._get_question_repository(),
        )

    # ==========================================================================
    #   Configuración (útil para tests/customización)
    # ==========================================================================

    def with_text_extractor(self, text_extractor: TextExtractorPort) -> "ServiceFactory":
        """
        Sobrescribe el extractor de texto.

        Args:
            text_extractor: implementación personalizada.

        Returns:
            Self (permite encadenar métodos).
        """
        self._text_extractor = text_extractor
        return self

    def with_file_storage(self, file_storage: FileStorage) -> "ServiceFactory":
        """
        Sobrescribe el storage de archivos.

        Args:
            file_storage: implementación personalizada.

        Returns:
            Self (permite encadenar métodos).
        """
        self._file_storage = file_storage
        return self

    def with_notification_service(self, notification_service: NotificationServicePort) -> "ServiceFactory":
        """
        Inyecta un servicio de notificaciones personalizado.

        Args:
            notification_service: implementación personalizada.

        Returns:
            Self (permite encadenar métodos).
        """
        self._notification_service = notification_service
        return self


# ==============================================================================
#   Singleton suave (personalizable)
# ==============================================================================

_default_factory: Optional[ServiceFactory] = None


def get_service_factory() -> ServiceFactory:
    """
    Retorna la instancia por defecto de la fábrica.

    Permite un acceso tipo singleton sin impedir la personalización durante tests.
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ServiceFactory()
    return _default_factory


def reset_service_factory() -> None:
    """
    Reinicia la instancia por defecto de la fábrica.

    Útil en escenarios de testing donde se requiere un entorno limpio.
    """
    global _default_factory
    _default_factory = None
