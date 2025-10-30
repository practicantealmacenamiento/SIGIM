"""Factoría de servicios para resolver dependencias de infraestructura."""

from __future__ import annotations

from typing import Optional

from app.application.services.admin_services import (
    AdminActorService,
    AdminQuestionnaireService,
    AdminUserService,
)
from app.domain.ports.external_ports import FileStorage, TextExtractorPort
from app.domain.ports.repositories import ActorRepository
from app.infrastructure.adapters.external_adapters.storage import DjangoDefaultStorageAdapter
from app.infrastructure.adapters.external_adapters.vision_adapter import TextExtractorAdapter
from app.infrastructure.adapters.repositories import (
    DjangoActorRepository,
    DjangoAnswerRepository,
    DjangoChoiceRepository,
    DjangoQuestionRepository,
    DjangoQuestionnaireRepository,
    DjangoSubmissionRepository,
)

__all__ = ["ServiceFactory", "get_service_factory", "reset_service_factory"]


class ServiceFactory:
    """Administra instancias compartidas de repositorios y servicios."""

    def __init__(self) -> None:
        self._answer_repo: Optional[DjangoAnswerRepository] = None
        self._submission_repo: Optional[DjangoSubmissionRepository] = None
        self._question_repo: Optional[DjangoQuestionRepository] = None
        self._choice_repo: Optional[DjangoChoiceRepository] = None
        self._questionnaire_repo: Optional[DjangoQuestionnaireRepository] = None
        self._actor_repo: Optional[ActorRepository] = None

        self._file_storage: Optional[FileStorage] = None
        self._text_extractor: Optional[TextExtractorPort] = None

        self._admin_actor_service: Optional[AdminActorService] = None
        self._admin_user_service: Optional[AdminUserService] = None
        self._admin_questionnaire_service: Optional[AdminQuestionnaireService] = None

    # ------------------------------------------------------------------
    # Repositorios
    # ------------------------------------------------------------------

    def _get_actor_repository(self) -> ActorRepository:
        if self._actor_repo is None:
            self._actor_repo = DjangoActorRepository()
        return self._actor_repo

    def _get_answer_repository(self) -> DjangoAnswerRepository:
        if self._answer_repo is None:
            self._answer_repo = DjangoAnswerRepository()
        return self._answer_repo

    def _get_submission_repository(self) -> DjangoSubmissionRepository:
        if self._submission_repo is None:
            self._submission_repo = DjangoSubmissionRepository()
        return self._submission_repo

    def _get_question_repository(self) -> DjangoQuestionRepository:
        if self._question_repo is None:
            self._question_repo = DjangoQuestionRepository()
        return self._question_repo

    def get_question_repository(self) -> DjangoQuestionRepository:
        """Expone el repositorio de preguntas ya inicializado."""

        return self._get_question_repository()

    def _get_choice_repository(self) -> DjangoChoiceRepository:
        if self._choice_repo is None:
            self._choice_repo = DjangoChoiceRepository()
        return self._choice_repo

    def _get_questionnaire_repository(self) -> DjangoQuestionnaireRepository:
        if self._questionnaire_repo is None:
            self._questionnaire_repo = DjangoQuestionnaireRepository()
        return self._questionnaire_repo

    def get_questionnaire_repository(self) -> DjangoQuestionnaireRepository:
        """Expone el repositorio de cuestionarios ya inicializado."""

        return self._get_questionnaire_repository()

    # ------------------------------------------------------------------
    # Puertos externos
    # ------------------------------------------------------------------

    def _get_file_storage(self) -> FileStorage:
        if self._file_storage is None:
            self._file_storage = DjangoDefaultStorageAdapter()
        return self._file_storage

    def _get_text_extractor(self) -> TextExtractorPort:
        if self._text_extractor is None:
            self._text_extractor = TextExtractorAdapter(mode="text", language_hints=["es", "en"])
        return self._text_extractor

    # ------------------------------------------------------------------
    # Servicios de aplicación
    # ------------------------------------------------------------------

    def create_answer_service(self):
        from app.application.services.services import AnswerService

        return AnswerService(repo=self._get_answer_repository(), storage=self._get_file_storage())

    def create_submission_service(self):
        from app.application.services.services import SubmissionService

        return SubmissionService(
            submission_repo=self._get_submission_repository(),
            answer_repo=self._get_answer_repository(),
            question_repo=self._get_question_repository(),
        )

    def create_questionnaire_service(self):
        from app.application.questionnaire import QuestionnaireService

        return QuestionnaireService(
            answer_repo=self._get_answer_repository(),
            submission_repo=self._get_submission_repository(),
            question_repo=self._get_question_repository(),
            choice_repo=self._get_choice_repository(),
            storage=self._get_file_storage(),
        )

    def create_history_service(self):
        from app.application.services.services import HistoryService

        return HistoryService(
            submission_repo=self._get_submission_repository(),
            answer_repo=self._get_answer_repository(),
            question_repo=self._get_question_repository(),
        )

    def create_verification_service(self):
        from app.application.verification import VerificationService

        return VerificationService(
            text_extractor=self._get_text_extractor(),
            question_repo=self._get_question_repository(),
        )

    # ------------------------------------------------------------------
    # Servicios administrativos
    # ------------------------------------------------------------------

    def create_admin_actor_service(self) -> AdminActorService:
        if self._admin_actor_service is None:
            self._admin_actor_service = AdminActorService()
        return self._admin_actor_service

    def create_admin_user_service(self) -> AdminUserService:
        if self._admin_user_service is None:
            self._admin_user_service = AdminUserService()
        return self._admin_user_service

    def create_admin_questionnaire_service(self) -> AdminQuestionnaireService:
        if self._admin_questionnaire_service is None:
            self._admin_questionnaire_service = AdminQuestionnaireService()
        return self._admin_questionnaire_service

    # ------------------------------------------------------------------
    # Configuración auxiliar
    # ------------------------------------------------------------------

    def with_text_extractor(self, text_extractor: TextExtractorPort) -> "ServiceFactory":
        self._text_extractor = text_extractor
        return self

    def with_file_storage(self, file_storage: FileStorage) -> "ServiceFactory":
        self._file_storage = file_storage
        return self


# ---------------------------------------------------------------------------
# Singleton perezoso
# ---------------------------------------------------------------------------

_default_factory: Optional[ServiceFactory] = None


def get_service_factory() -> ServiceFactory:
    """Devuelve la instancia compartida de ServiceFactory."""

    global _default_factory
    if _default_factory is None:
        _default_factory = ServiceFactory()
    return _default_factory


def reset_service_factory() -> None:
    """Restablece la instancia compartida (útil en pruebas)."""

    global _default_factory
    _default_factory = None
