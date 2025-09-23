"""
Service Factory for Dependency Injection

This module implements the Factory pattern to centralize the creation and 
configuration of application services with their dependencies.

Following Clean Architecture principles:
- All dependencies flow inward toward the domain
- Infrastructure implementations are injected into application services
- Services depend only on domain interfaces (ports and repositories)
"""

from __future__ import annotations

from typing import Optional

# Import application services lazily to avoid circular dependencies

from app.domain.ports import TextExtractorPort, FileStorage, NotificationServicePort

from app.infrastructure.repositories import (
    DjangoAnswerRepository,
    DjangoSubmissionRepository,
    DjangoQuestionRepository,
    DjangoChoiceRepository,
    DjangoQuestionnaireRepository,
)
from app.infrastructure.storage import DjangoDefaultStorageAdapter

from app.infrastructure.vision_adapter import TextExtractorAdapter


class ServiceFactory:
    """
    Factory for creating application services with proper dependency injection.
    
    This factory centralizes the creation of services and ensures that all
    dependencies are properly injected following the dependency inversion principle.
    
    Usage:
        factory = ServiceFactory()
        answer_service = factory.create_answer_service()
        submission_service = factory.create_submission_service()
    """

    def __init__(self):
        """Initialize the factory with default configurations."""
        self._answer_repo = None
        self._submission_repo = None
        self._question_repo = None
        self._choice_repo = None
        self._questionnaire_repo = None
        self._file_storage = None
        self._text_extractor = None
        self._notification_service = None

    # Repository factories (lazy initialization)
    def _get_answer_repository(self):
        """Get or create Answer repository instance."""
        if self._answer_repo is None:
            self._answer_repo = DjangoAnswerRepository()
        return self._answer_repo

    def _get_submission_repository(self):
        """Get or create Submission repository instance."""
        if self._submission_repo is None:
            self._submission_repo = DjangoSubmissionRepository()
        return self._submission_repo

    def _get_question_repository(self):
        """Get or create Question repository instance."""
        if self._question_repo is None:
            self._question_repo = DjangoQuestionRepository()
        return self._question_repo

    def _get_choice_repository(self):
        """Get or create Choice repository instance."""
        if self._choice_repo is None:
            self._choice_repo = DjangoChoiceRepository()
        return self._choice_repo

    def _get_questionnaire_repository(self):
        """Get or create Questionnaire repository instance."""
        if self._questionnaire_repo is None:
            self._questionnaire_repo = DjangoQuestionnaireRepository()
        return self._questionnaire_repo

    # Port factories (lazy initialization)
    def _get_file_storage(self) -> FileStorage:
        """Get or create FileStorage port implementation."""
        if self._file_storage is None:
            self._file_storage = DjangoDefaultStorageAdapter()
        return self._file_storage

    def _get_text_extractor(self) -> TextExtractorPort:
        """Get or create TextExtractor port implementation."""
        if self._text_extractor is None:
            self._text_extractor = TextExtractorAdapter(
                mode="text",
                language_hints=["es", "en"]
            )
        return self._text_extractor

    def _get_notification_service(self) -> Optional[NotificationServicePort]:
        """Get or create NotificationService port implementation."""
        # TODO: Implement notification service adapter when needed
        return self._notification_service

    # Service creation methods
    def create_answer_service(self):
        """
        Create AnswerService with all required dependencies injected.
        
        Returns:
            AnswerService: Configured service instance
        """
        from app.application.services import AnswerService
        return AnswerService(
            repo=self._get_answer_repository(),
            storage=self._get_file_storage()
        )

    def create_submission_service(self):
        """
        Create SubmissionService with all required dependencies injected.
        
        Returns:
            SubmissionService: Configured service instance
        """
        from app.application.services import SubmissionService
        return SubmissionService(
            submission_repo=self._get_submission_repository(),
            answer_repo=self._get_answer_repository(),
            question_repo=self._get_question_repository()
        )

    def create_questionnaire_service(self):
        """
        Create QuestionnaireService with all required dependencies injected.
        
        Returns:
            QuestionnaireService: Configured service instance
        """
        from app.application.questionnaire import QuestionnaireService
        return QuestionnaireService(
            answer_repo=self._get_answer_repository(),
            submission_repo=self._get_submission_repository(),
            question_repo=self._get_question_repository(),
            choice_repo=self._get_choice_repository(),
            storage=self._get_file_storage()
        )

    def create_history_service(self):
        """
        Create HistoryService with all required dependencies injected.
        
        Returns:
            HistoryService: Configured service instance
        """
        from app.application.services import HistoryService
        return HistoryService(
            submission_repo=self._get_submission_repository(),
            answer_repo=self._get_answer_repository(),
            question_repo=self._get_question_repository()
        )

    def create_verification_service(self):
        """
        Create VerificationService with all required dependencies injected.
        
        Returns:
            VerificationService: Configured service instance
        """
        from app.application.verification import VerificationService
        return VerificationService(
            text_extractor=self._get_text_extractor(),
            question_repo=self._get_question_repository()
        )

    # Configuration methods for testing and customization
    def with_text_extractor(self, text_extractor: TextExtractorPort) -> 'ServiceFactory':
        """
        Configure factory with a custom TextExtractor implementation.
        
        Args:
            text_extractor: Custom TextExtractor implementation
            
        Returns:
            ServiceFactory: Self for method chaining
        """
        self._text_extractor = text_extractor
        return self

    def with_file_storage(self, file_storage: FileStorage) -> 'ServiceFactory':
        """
        Configure factory with a custom FileStorage implementation.
        
        Args:
            file_storage: Custom FileStorage implementation
            
        Returns:
            ServiceFactory: Self for method chaining
        """
        self._file_storage = file_storage
        return self

    def with_notification_service(self, notification_service: NotificationServicePort) -> 'ServiceFactory':
        """
        Configure factory with a custom NotificationService implementation.
        
        Args:
            notification_service: Custom NotificationService implementation
            
        Returns:
            ServiceFactory: Self for method chaining
        """
        self._notification_service = notification_service
        return self


# Global factory instance for application use
_default_factory = None


def get_service_factory() -> ServiceFactory:
    """
    Get the default service factory instance.
    
    This function provides a singleton-like access to the service factory
    while still allowing for customization and testing.
    
    Returns:
        ServiceFactory: The default factory instance
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ServiceFactory()
    return _default_factory


def reset_service_factory() -> None:
    """
    Reset the default service factory instance.
    
    This is primarily useful for testing scenarios where you need
    a fresh factory instance.
    """
    global _default_factory
    _default_factory = None