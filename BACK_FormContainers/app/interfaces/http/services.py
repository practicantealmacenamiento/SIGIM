"""Servicios de apoyo para la capa de interfaces HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Tuple
from uuid import UUID

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from app.domain.exceptions import DomainException
from app.interfaces.exception_handlers import translate_domain_exception
from app.infrastructure.serializers import (
    ActorModelSerializer,
    AnswerReadSerializer,
    HistorialItemSerializer,
    QuestionModelSerializer,
    QuestionnaireListItemSerializer,
    QuestionnaireModelSerializer,
    SaveAndAdvanceInputSerializer,
    SaveAndAdvanceResponseSerializer,
    SubmissionCreateSerializer,
    SubmissionModelSerializer,
    VerificationInputSerializer,
    VerificationResponseSerializer,
)
from app.infrastructure.models import Actor


TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def _as_bool(value, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in TRUE_VALUES


def _parse_uuid(value, *, field: str) -> Tuple[Optional[UUID], Optional[Response]]:
    try:
        return UUID(str(value)), None
    except (ValueError, TypeError):
        return None, Response({field: f"{field} inválido."}, status=status.HTTP_400_BAD_REQUEST)


def _parse_date(value, *, field: str) -> Tuple[Optional[datetime.date], Optional[Response]]:
    if not value:
        return None, None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date(), None
    except ValueError:
        return None, Response({field: "Usa formato YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)


def _build_paginator() -> PageNumberPagination:
    paginator = PageNumberPagination()
    paginator.page_size = 20
    paginator.page_size_query_param = "page_size"
    paginator.max_page_size = 100
    return paginator


@dataclass
class InterfaceServices:
    questionnaire_service: Any
    submission_service: Any
    history_service: Any
    verification_service: Any


class AuthAPIService:
    def __init__(self, *, build_user_payload, auth_login_issue_token, auth_logout_revoke_token):
        self.build_user_payload = build_user_payload
        self.auth_login_issue_token = auth_login_issue_token
        self.auth_logout_revoke_token = auth_logout_revoke_token

    def login(self, request, serializer) -> Response:
        from django.contrib.auth import login as dj_login

        data = serializer.validated_data
        try:
            user, token_key = self.auth_login_issue_token(data["identifier"], data["password"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        dj_login(request, user)
        payload = {"token": token_key, "user": self.build_user_payload(user)}
        return _set_auth_cookies(Response(payload), request, user)

    def whoami(self, request) -> Response:
        payload = {
            "user": self.build_user_payload(request.user),
            "auth_via": "token" if request.auth else "session",
        }
        return _set_auth_cookies(Response(payload), request, request.user)

    def logout(self, request) -> Response:
        from django.contrib.auth import logout as dj_logout

        dj_logout(request)
        self.auth_logout_revoke_token(request.user)
        return _clear_auth_cookies(Response({"detail": "ok"}))


class VerificationAPIService:
    def __init__(self, verification_service):
        self.service = verification_service

    def verify(self, request) -> Response:
        serializer = VerificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.service.verify_with_question(
                serializer.validated_data["question_id"],
                request.FILES["imagen"],
            )
        except DomainException as exc:
            return translate_domain_exception(exc)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(VerificationResponseSerializer(result).data)


class QuestionnaireAPIService:
    def __init__(self, services: InterfaceServices):
        self.services = services

    def save_and_advance(self, request) -> Response:
        serializer = SaveAndAdvanceInputSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payload = serializer.to_domain_input()
        if not payload.get("answer_text") and "value" in request.data:
            raw_value = request.data.get("value")
            payload["answer_text"] = None if raw_value is None else str(raw_value)
        payload["user_id"] = getattr(request.user, "id", None)
        from app.application.commands import SaveAndAdvanceCommand

        cmd = SaveAndAdvanceCommand(**payload)
        try:
            result = self.services.questionnaire_service.save_and_advance(cmd)
        except DomainException as exc:
            return translate_domain_exception(exc)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(SaveAndAdvanceResponseSerializer(result).data)

    def first_question(self, request) -> Response:
        raw_qid = request.query_params.get("questionnaire_id")
        if not raw_qid:
            return Response({"error": "Falta 'questionnaire_id'."}, status=status.HTTP_400_BAD_REQUEST)
        questionnaire_id, error = _parse_uuid(raw_qid, field="questionnaire_id")
        if error:
            return error
        question = self.services.questionnaire_service.get_first_question(questionnaire_id)
        from app.infrastructure.adapters.repositories import DjangoQuestionRepository

        question_model = DjangoQuestionRepository().get_by_id(str(question.id))
        if not question_model:
            return Response({"error": "Pregunta no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionModelSerializer(question_model).data)

    def list_catalog(self, request, questionnaire_repo) -> Response:
        include_questions = _as_bool(request.query_params.get("include_questions"))
        if include_questions:
            data = QuestionnaireModelSerializer(
                questionnaire_repo.list_all(),
                many=True,
                context={"request": request},
            ).data
        else:
            data = QuestionnaireListItemSerializer(
                questionnaire_repo.list_minimal(),
                many=True,
                context={"request": request},
            ).data
        return Response(data)

    def question_detail(self, request, question_repo, question_id: UUID) -> Response:
        question = question_repo.get(question_id)
        if not question:
            return Response({"detail": "Pregunta no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionModelSerializer(question, context={"request": request}).data)


class SubmissionAPIService:
    def __init__(self, services: InterfaceServices):
        self.services = services

    def create(self, request) -> Response:
        serializer = SubmissionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        submission = self.services.submission_service.create_submission(
            questionnaire_id=data["questionnaire_id"],
            tipo_fase=data["tipo_fase"],
            regulador_id=data.get("regulador_id"),
            placa_vehiculo=data.get("placa_vehiculo"),
            created_by=request.user,
        )
        return Response(SubmissionModelSerializer(submission, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def list(self, request) -> Response:
        qs = self.services.submission_service.list_submissions(
            request.query_params,
            user=request.user,
            include_all=_as_bool(getattr(request.user, "is_staff", False)),
        )
        paginator = _build_paginator()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            data = SubmissionModelSerializer(page, many=True, context={"request": request}).data
            return paginator.get_paginated_response(data)
        return Response(SubmissionModelSerializer(qs, many=True, context={"request": request}).data)

    def retrieve(self, request, pk: str) -> Response:
        obj = self.services.submission_service.get_submission_for_api(
            pk,
            user=request.user,
            include_all=_as_bool(getattr(request.user, "is_staff", False)),
        )
        if not obj:
            return Response({"error": "Submission no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SubmissionModelSerializer(obj, context={"request": request}).data)

    def finalize(self, request, pk: str) -> Response:
        try:
            updates = self.services.submission_service.finalize_submission(UUID(str(pk)))
        except DomainException as exc:
            return translate_domain_exception(exc)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Finalizada", "submission_id": str(pk), "updates": updates})

    def enriched_detail(self, request, pk: str) -> Response:
        try:
            detail = self.services.submission_service.get_detail(UUID(str(pk)))
        except DomainException as exc:
            return translate_domain_exception(exc)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "submission": SubmissionModelSerializer(detail["submission"], context={"request": request}).data,
                "answers": AnswerReadSerializer(detail["answers"], many=True, context={"request": request}).data,
            }
        )


class ActorAPIService:
    def list(self, request) -> Response:
        qs = Actor.objects.all()
        params = request.query_params
        activo = params.get("activo")
        if activo is None or _as_bool(activo, default=True):
            qs = qs.filter(activo=True)

        tipo = (params.get("tipo") or "").strip()
        if tipo:
            upper = tipo.upper()
            mapping = {"proveedor": "PROVEEDOR", "transportista": "TRANSPORTISTA", "receptor": "RECEPTOR"}
            qs = qs.filter(tipo=mapping.get(tipo.lower(), upper))

        term = (params.get("search") or params.get("q") or "").strip()
        if term:
            from django.db.models import Q

            qs = qs.filter(Q(nombre__icontains=term) | Q(documento__icontains=term))

        try:
            limit = max(1, min(int(params.get("limit", "15") or 15), 100))
        except Exception:
            limit = 15

        qs = qs.order_by("nombre")[:limit]
        return Response(ActorModelSerializer(qs, many=True).data)


class HistoryAPIService:
    def __init__(self, services: InterfaceServices):
        self.services = services

    def list(self, request) -> Response:
        fecha_desde, error = _parse_date(request.query_params.get("fecha_desde"), field="fecha_desde")
        if error:
            return error
        fecha_hasta, error = _parse_date(request.query_params.get("fecha_hasta"), field="fecha_hasta")
        if error:
            return error

        items = self.services.history_service.list_history(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            solo_completados=_as_bool(request.query_params.get("solo_completados")),
            user=request.user,
            include_all=_as_bool(getattr(request.user, "is_staff", False)),
        )
        return Response(HistorialItemSerializer(items, many=True, context={"request": request}).data)


class MediaAPIService:
    def serve(self, *, file_path: str) -> Response:
        normalized = os.path.normpath(file_path or "").replace("\\", "/")

        if not normalized or normalized.startswith("/") or normalized.startswith("..") or "/../" in f"/{normalized}/":
            return Response({"detail": "Ruta inválida."}, status=status.HTTP_400_BAD_REQUEST)

        media_prefix = (settings.MEDIA_URL or "").lstrip("/")
        if media_prefix and normalized.startswith(media_prefix):
            normalized = normalized[len(media_prefix):].lstrip("/")

        if ".." in normalized.split("/"):
            return Response({"detail": "Ruta inválida."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_storage.exists(normalized):
            return Response({"detail": "Archivo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        content_type, _ = mimetypes.guess_type(normalized)
        file_handle = default_storage.open(normalized, "rb")
        response = FileResponse(file_handle, content_type=content_type or "application/octet-stream")
        response["Content-Disposition"] = f'inline; filename="{os.path.basename(normalized)}"'
        return response


def _set_auth_cookies(resp: Response, request, user) -> Response:
    from django.middleware.csrf import get_token

    csrftoken = get_token(request)
    resp.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrftoken,
        secure=settings.CSRF_COOKIE_SECURE,
        samesite=settings.CSRF_COOKIE_SAMESITE,
    )
    resp.set_cookie(
        "is_staff",
        "1" if getattr(user, "is_staff", False) else "0",
        secure=settings.CSRF_COOKIE_SECURE,
        samesite="Lax",
    )
    resp.set_cookie(
        "auth_username",
        user.get_username(),
        secure=settings.CSRF_COOKIE_SECURE,
        samesite="Lax",
    )
    return resp


def _clear_auth_cookies(resp: Response) -> Response:
    for name in (settings.CSRF_COOKIE_NAME, "is_staff", "auth_username"):
        resp.delete_cookie(name)
    return resp


# Importaciones tardías para evitar ciclos
import mimetypes
import os
