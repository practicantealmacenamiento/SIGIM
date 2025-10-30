"""Servicios HTTP de la capa interfaces."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from app.application.verification import InvalidImageError
from app.domain.exceptions import DomainException
from app.domain.ports.repositories import AnswerRepository
from app.infrastructure.serializers import (
    QuestionnaireModelSerializer,
    SubmissionModelSerializer,
)


class InterfaceServices:
    """Resolver QuerySet de servicios de aplicacion."""

    def __init__(self) -> None:
        from app.infrastructure.factories import get_service_factory

        factory = get_service_factory()
        self.answer_service = factory.create_answer_service()
        self.submission_service = factory.create_submission_service()
        self.history_service = factory.create_history_service()
        self.verification_service = factory.create_verification_service()
        self.questionnaire_service = factory.create_questionnaire_service()
        self.answer_repo: AnswerRepository = factory._get_answer_repository()


services = InterfaceServices()


def translate_domain_exception(exc: DomainException) -> Response:
    """Convierte una excepcion del dominio en respuesta HTTP."""

    payload = {"detail": exc.message}
    if exc.details:
        payload["details"] = exc.details

    status_map = {
        "ValidationError": status.HTTP_400_BAD_REQUEST,
        "EntityNotFoundError": status.HTTP_404_NOT_FOUND,
        "BusinessRuleViolationError": status.HTTP_400_BAD_REQUEST,
        "InvalidOperationError": status.HTTP_400_BAD_REQUEST,
        "InvariantViolationError": status.HTTP_409_CONFLICT,
    }
    code = status_map.get(exc.__class__.__name__, status.HTTP_400_BAD_REQUEST)
    return Response(payload, status=code)


# ---------------------------------------------------------------------------
# Herramientas auxiliares
# ---------------------------------------------------------------------------


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _parse_date(value: Optional[str], *, field: str):
    if not value:
        return None, None
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, Response({field: "Formato de fecha invalido (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Servicios HTTP
# ---------------------------------------------------------------------------


class SubmissionAPIService:
    def __init__(self, services: InterfaceServices):
        self.services = services

    def list(self, request: Request) -> Response:
        params = request.query_params
        only_finalized = params.get("solo_finalizados")
        include_drafts = params.get("incluir_borradores")

        filters: Dict[str, Any] = {}
        if _as_bool(only_finalized):
            filters["solo_finalizados"] = True
        if not _as_bool(include_drafts, default=True):
            filters["solo_finalizados"] = True
        if plac := params.get("placa_vehiculo"):
            filters["placa_vehiculo"] = plac
        if cont := params.get("contenedor"):
            filters["contenedor"] = cont

        submissions = self.services.submission_service.list_submissions(
            filters,
            user=request.user,
            include_all=_as_bool(getattr(request.user, "is_staff", False)),
        )
        return Response(SubmissionModelSerializer(submissions, many=True, context={"request": request}).data)

    def create(self, request: Request) -> Response:
        data = {key: (value.strip() if isinstance(value, str) else value) for key, value in request.data.items()}

        try:
            submission = self.services.submission_service.create_submission(
                questionnaire_id=UUID(str(data.get("questionnaire_id"))),
                tipo_fase=data.get("tipo_fase", "entrada"),
                regulador_id=UUID(str(data["regulador_id"])) if data.get("regulador_id") else None,
                placa_vehiculo=data.get("placa_vehiculo"),
                created_by=request.user,
            )
        except DomainException as exc:
            return translate_domain_exception(exc)

        return Response(
            SubmissionModelSerializer(submission, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request: Request, pk: str) -> Response:
        try:
            submission = self.services.submission_service.get_submission_for_api(UUID(pk), user=request.user)
        except DomainException as exc:
            return translate_domain_exception(exc)

        if submission is None:
            return Response({"detail": "Submission no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        return Response(SubmissionModelSerializer(submission, context={"request": request}).data)

    def patch(self, request: Request, pk: str) -> Response:
        try:
            submission = self.services.submission_service.get_submission_for_api(UUID(pk), user=request.user)
        except DomainException as exc:
            return translate_domain_exception(exc)

        if submission is None:
            return Response({"detail": "Submission no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        updates = {k: v for k, v in request.data.items() if v not in (None, "")}
        self.services.submission_service.submission_repo.save_partial_updates(UUID(pk), **updates)
        return Response({"detail": "Actualizado."})


class QuestionnaireAPIService:
    def __init__(self, services: InterfaceServices):
        self.services = services

    def list(self, request: Request) -> Response:
        qs = self.services.questionnaire_service.questionnaire_repo.list_all()
        return Response(QuestionnaireModelSerializer(qs, many=True).data)

    def detail(self, request: Request, pk: str) -> Response:
        try:
            questionnaire = self.services.questionnaire_service.questionnaire_repo.get_by_id(UUID(pk))
        except Exception:
            questionnaire = None
        if not questionnaire:
            return Response({"detail": "Cuestionario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionnaireModelSerializer(questionnaire).data)


class VerificationAPIService:
    def __init__(self, services: InterfaceServices):
        self.services = services

    def verify_precinto(self, request: Request) -> Response:
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Archivo requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = self.services.verification_service.verificar_precinto(file.read())
        except InvalidImageError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result)
