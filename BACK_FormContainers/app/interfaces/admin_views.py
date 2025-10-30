"""Vistas administrativas soportadas por servicios de aplicacion."""

from __future__ import annotations

from typing import Optional

from django.shortcuts import get_object_or_404

from rest_framework import status, serializers, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from .auth import BearerOrTokenAuthentication

from app.application.services.admin_services import (
    AdminActorService,
    AdminQuestionnaireService,
    AdminUserService,
)
from app.infrastructure.models import Actor, Questionnaire
from app.infrastructure.serializers import (
    ActorModelSerializer,
    QuestionnaireListItemSerializer,
    QuestionnaireModelSerializer,
)


class AdminPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class AdminAuthMixin:
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAdminUser]
    pagination_class = AdminPageNumberPagination

    @property
    def factory(self):
        from app.infrastructure.factories import get_service_factory

        return get_service_factory()

    def paginate_queryset(self, request, queryset, *, serializer_cls, context: Optional[dict] = None):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is None:
            return Response(serializer_cls(queryset, many=True, context=context).data)
        data = serializer_cls(page, many=True, context=context).data
        return paginator.get_paginated_response(data)

    def actor_service(self) -> AdminActorService:
        return self.factory.create_admin_actor_service()

    def user_service(self) -> AdminUserService:
        return self.factory.create_admin_user_service()

    def questionnaire_service(self) -> AdminQuestionnaireService:
        return self.factory.create_admin_questionnaire_service()


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------


class AdminActorViewSet(AdminAuthMixin, viewsets.ViewSet):
    """Gestion del catalogo de actores para administradores."""

    @extend_schema(
        tags=["admin/actors"],
        summary="Listar actores (admin)",
        parameters=[
            OpenApiParameter(name="search", required=False, type=str),
            OpenApiParameter(name="tipo", required=False, type=str),
            OpenApiParameter(name="page", required=False, type=int),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses={200: OpenApiResponse(description="OK")},
    )
    def list(self, request: Request):
        params = request.query_params
        qs = self.actor_service().filtered_queryset(
            search=params.get("search") or params.get("q") or params.get("term") or "",
            tipo=params.get("tipo") or "",
        )
        return self.paginate_queryset(request, qs, serializer_cls=ActorModelSerializer)

    @extend_schema(tags=["admin/actors"], summary="Detalle actor")
    def retrieve(self, request: Request, pk: str = None):
        actor = get_object_or_404(Actor, pk=pk)
        return Response(ActorModelSerializer(actor).data)

    @extend_schema(tags=["admin/actors"], summary="Crear actor")
    def create(self, request: Request):
        actor = self.actor_service().create(request.data)
        return Response(ActorModelSerializer(actor).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["admin/actors"], summary="Actualizar parcialmente actor (PATCH)")
    def partial_update(self, request: Request, pk: str = None):
        actor = get_object_or_404(Actor, pk=pk)
        updated = self.actor_service().update(actor, request.data)
        return Response(ActorModelSerializer(updated).data)

    @extend_schema(tags=["admin/actors"], summary="Eliminar actor")
    def destroy(self, request: Request, pk: str = None):
        actor = get_object_or_404(Actor, pk=pk)
        self.actor_service().delete(actor)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class AdminUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    is_staff = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)


class AdminUserViewSet(AdminAuthMixin, viewsets.ViewSet):
    """CRUD minimo de usuarios para administracion."""

    @extend_schema(tags=["admin/users"], summary="Listar usuarios")
    def list(self, request: Request):
        users = self.user_service().list_all()
        return Response(AdminUserSerializer(users, many=True).data)

    @extend_schema(tags=["admin/users"], summary="Detalle usuario")
    def retrieve(self, request: Request, pk: str = None):
        user = get_object_or_404(self.user_service().list_all(), pk=pk)
        return Response(AdminUserSerializer(user).data)

    @extend_schema(tags=["admin/users"], summary="Crear usuario")
    def create(self, request: Request):
        serializer = AdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.user_service().create(serializer.validated_data)
        return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["admin/users"], summary="Actualizar usuario (PUT)")
    def update(self, request: Request, pk: str = None):
        serializer = AdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(self.user_service().list_all(), pk=pk)
        updated = self.user_service().update(user, serializer.validated_data, partial=False)
        return Response(AdminUserSerializer(updated).data)

    @extend_schema(tags=["admin/users"], summary="Actualizar usuario (PATCH)")
    def partial_update(self, request: Request, pk: str = None):
        serializer = AdminUserSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(self.user_service().list_all(), pk=pk)
        updated = self.user_service().update(user, serializer.validated_data, partial=True)
        return Response(AdminUserSerializer(updated).data)

    @extend_schema(tags=["admin/users"], summary="Eliminar usuario")
    def destroy(self, request: Request, pk: str = None):
        user = get_object_or_404(self.user_service().list_all(), pk=pk)
        self.user_service().delete(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Questionnaires
# ---------------------------------------------------------------------------


class AdminQuestionnaireViewSet(AdminAuthMixin, viewsets.ViewSet):
    """CRUD administrativo de cuestionarios delegando la logica a servicios."""

    def _handle_service_error(self, exc: ValueError) -> Response:
        mapping = {
            "title_required": {"title": "El titulo es obligatorio."},
            "title_blank": {"title": "El titulo no puede estar vacio."},
            "version_blank": {"version": "La version no puede estar vacia."},
            "timezone_blank": {"timezone": "La zona horaria no puede estar vacia."},
            "question_text_blank": {"questions": "Cada pregunta debe tener texto."},
            "choice_text_blank": {"choices": "Cada opcion debe tener texto."},
        }
        return Response(mapping.get(str(exc), {"detail": str(exc)}), status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Listar cuestionarios (admin)",
        parameters=[
            OpenApiParameter(name="search", required=False, type=str),
            OpenApiParameter(name="page", required=False, type=int),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses={200: QuestionnaireListItemSerializer(many=True)},
    )
    def list(self, request: Request):
        qs = self.questionnaire_service().filtered_queryset(search=request.query_params.get("search", ""))
        return self.paginate_queryset(request, qs, serializer_cls=QuestionnaireListItemSerializer)

    @extend_schema(tags=["admin/questionnaires"], summary="Detalle de cuestionario", responses={200: QuestionnaireModelSerializer})
    def retrieve(self, request: Request, pk: str = None):
        qn = self.questionnaire_service().retrieve(pk)
        if not qn:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionnaireModelSerializer(qn).data)

    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Crear cuestionario",
        request=serializers.DictField,
        responses={201: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validacion")},
    )
    def create(self, request: Request):
        service = self.questionnaire_service()
        try:
            qn = service.create(request.data or {})
        except ValueError as exc:
            return self._handle_service_error(exc)
        return Response(QuestionnaireModelSerializer(qn).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Actualizar cuestionario (PUT)",
        request=serializers.DictField,
        responses={200: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validacion")},
    )
    def update(self, request: Request, pk: str = None):
        return self._upsert(pk=pk, payload=request.data, is_partial=False)

    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Actualizar cuestionario (PATCH)",
        request=serializers.DictField,
        responses={200: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validacion")},
    )
    def partial_update(self, request: Request, pk: str = None):
        return self._upsert(pk=pk, payload=request.data, is_partial=True)

    @extend_schema(tags=["admin/questionnaires"], summary="Eliminar", responses={204: OpenApiResponse(description="OK")})
    def destroy(self, request: Request, pk: str = None):
        questionnaire = get_object_or_404(Questionnaire, pk=pk)
        self.questionnaire_service().delete(questionnaire)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _upsert(self, *, pk: str, payload: dict, is_partial: bool):
        service = self.questionnaire_service()
        try:
            qn = service.update(questionnaire_id=pk, payload=payload or {}, is_partial=is_partial)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return self._handle_service_error(exc)
        return Response(QuestionnaireModelSerializer(qn).data)
