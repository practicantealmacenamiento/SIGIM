from __future__ import annotations

import os
from uuid import UUID

from django.conf import settings
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    extend_schema,
    OpenApiTypes,
    OpenApiParameter,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView  # ⬅️ NUEVO

# ===== Aplicación / Casos de uso =====
from app.application.commands import SaveAndAdvanceCommand
from app.application.services import SubmissionService, HistoryService
from app.application.questionnaire import QuestionnaireService
from app.application.verification import VerificationService, InvalidImage, ExtractionFailed
from app.domain.exceptions import DomainException

# ===== Manejo de excepciones =====
from app.interfaces.exception_handlers import translate_domain_exception

# ===== Infraestructura / Adaptadores =====
from app.infrastructure.serializers import (
    QuestionModelSerializer,
    SubmissionModelSerializer,
    SubmissionCreateSerializer,
    ActorModelSerializer,
    SaveAndAdvanceInputSerializer,
    SaveAndAdvanceResponseSerializer,
    AnswerReadSerializer,
    VerificationResponseSerializer,
    VerificationInputSerializer,
    QuestionnaireListItemSerializer,
    HistorialItemSerializer,
)
from app.infrastructure.factories import get_service_factory
from app.infrastructure.repositories import DjangoSubmissionRepository, DjangoQuestionnaireRepository
from app.infrastructure.models import Question as QuestionModel


# ===============================
# VISTAS PRIVADAS DE ESQUEMA/DOCS (requiere staff) — NUEVO
# ===============================
class PrivateSchemaAPIView(SpectacularAPIView):
    """
    /api/schema/ — sólo visible a staff.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


class PrivateSwaggerUIView(SpectacularSwaggerView):
    """
    /api/docs/ — sólo visible a staff.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


# ===============================
# Verificación (OCR) — autenticado
# ===============================
class VerificacionUniversalAPIView(APIView):
    """
    Universal OCR verification endpoint.
    Handles only HTTP concerns and delegates completely to VerificationService.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_verification_service(self):
        """Factory method for dependency injection."""
        return self._factory.create_verification_service()

    @extend_schema(
        request=VerificationInputSerializer,
        responses={200: VerificationResponseSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Verificación"],
        description="OCR (Google Vision) + reglas por semantic_tag (placa, precinto, contenedor). Requiere usuario autenticado.",
    )
    def post(self, request):
        """Handle OCR verification request - validates input and delegates to service."""
        # Input validation only
        serializer = VerificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Extract image file from request
        if "imagen" not in request.FILES:
            return Response({"error": "Se requiere una imagen."}, status=400)
        
        imagen_file = request.FILES["imagen"]

        # Delegate completely to verification service
        try:
            service = self._get_verification_service()
            result = service.verify_with_question(data["question_id"], imagen_file)
            
            return Response(VerificationResponseSerializer(result).data)
        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response(
                {"error": "Error interno del servidor", "type": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================
# Cuestionario (primera pregunta) — autenticado
# ==========================================
class PrimeraPreguntaAPIView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("questionnaire_id", OpenApiTypes.UUID, required=False)],
        responses={200: QuestionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Primera pregunta de un cuestionario (por orden). Requiere usuario autenticado.",
    )
    def get(self, request):
        qid = request.query_params.get("questionnaire_id")
        if qid:
            try:
                # Usar el repositorio para obtener las preguntas del cuestionario
                from app.infrastructure.repositories import DjangoQuestionRepository
                repo = DjangoQuestionRepository()
                questions = repo.list_by_questionnaire(UUID(qid))
                if not questions:
                    return Response({"error": "No se encontraron preguntas para este cuestionario."}, status=404)
                # Obtener la primera pregunta por orden
                first_question = min(questions, key=lambda q: q.order)
                # Convertir la entidad de dominio a modelo para serialización
                pregunta = QuestionModel.objects.get(id=first_question.id)
                return Response(QuestionModelSerializer(pregunta).data)
            except (ValueError, QuestionModel.DoesNotExist):
                return Response({"error": "Cuestionario no válido o pregunta no encontrada."}, status=404)
        else:
            # Si no se especifica cuestionario, obtener la primera pregunta de cualquier cuestionario
            pregunta = QuestionModel.objects.order_by("order").first()
            if not pregunta:
                return Response({"error": "No se encontró ninguna pregunta."}, status=404)
            return Response(QuestionModelSerializer(pregunta).data)


# ==========================================
# Guardar y Avanzar — autenticado (no admin)
# ==========================================
class GuardarYAvanzarAPIView(APIView):
    """
    Save answer and advance to next question.
    Simplified to only handle HTTP concerns and delegate to QuestionnaireService.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_questionnaire_service(self):
        """Factory method for dependency injection."""
        return self._factory.create_questionnaire_service()

    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar",
        tags=["Cuestionario"],
        description="Guarda una respuesta y devuelve la siguiente pregunta. Requiere usuario autenticado.",
    )
    def post(self, request):
        """Handle save and advance request - validates input and delegates to service."""
        # Input validation
        serializer = SaveAndAdvanceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Prepare file uploads (handle legacy and new formats)
        uploads = self._prepare_uploads(request, data)

        # Create command
        cmd = SaveAndAdvanceCommand(
            submission_id=data["submission_id"],
            question_id=data["question_id"],
            user_id=data.get("user_id"),
            answer_text=data.get("answer_text"),
            answer_choice_id=data.get("answer_choice_id"),
            uploads=uploads,
        )

        # Delegate to service and handle domain exceptions consistently
        try:
            service = self._get_questionnaire_service()
            result = service.save_and_advance(cmd)
            return Response(
                SaveAndAdvanceResponseSerializer(result, context={"request": request}).data
            )
        except DomainException as e:
            return translate_domain_exception(e)
        except DjangoValidationError as e:
            # Handle Django validation errors separately as they're not domain exceptions
            error_message = getattr(e, "message_dict", str(e))
            return Response(
                {"error": error_message, "type": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Error interno del servidor", "type": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _prepare_uploads(self, request, data):
        """Prepare file uploads from request - handles legacy and new formats."""
        uploads = []
        
        # Legacy format: answer_file list
        legacy = request.FILES.getlist("answer_file")
        if legacy:
            uploads.extend(legacy)
        
        # New format: individual fields
        if "answer_file" in data and data["answer_file"]:
            uploads.append(data["answer_file"])
        if "answer_file_extra" in data and data["answer_file_extra"]:
            uploads.append(data["answer_file_extra"])
        
        # Limit to maximum 2 files
        return uploads[:2] if len(uploads) > 2 else uploads


# ======================
# Submissions — autenticado
# ======================
class SubmissionViewSet(viewsets.ViewSet):
    """
    ViewSet for Submission operations.
    Delegates all business logic to application services.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_submission_service(self) -> SubmissionService:
        """Factory method for dependency injection."""
        return self._factory.create_submission_service()

    @extend_schema(
        parameters=[
            OpenApiParameter("incluir_borradores", OpenApiTypes.STR, required=False),
            OpenApiParameter("solo_finalizados", OpenApiTypes.STR, required=False),
            OpenApiParameter("tipo_fase", OpenApiTypes.STR, required=False),
            OpenApiParameter("proveedor_id", OpenApiTypes.UUID, required=False),
            OpenApiParameter("transportista_id", OpenApiTypes.UUID, required=False),
            OpenApiParameter("receptor_id", OpenApiTypes.UUID, required=False),
        ],
        responses={200: SubmissionModelSerializer(many=True)},
        tags=["Submissions"],
        description="Lista submissions con filtros. Requiere usuario autenticado.",
    )
    def list(self, request):
        """List submissions with filters - delegates to repository."""
        try:
            repo = DjangoSubmissionRepository()
            qs = repo.list_for_api(request.query_params)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(qs, request)
            if page is not None:
                serializer = SubmissionModelSerializer(
                    page, many=True, context={"request": request}
                )
                return paginator.get_paginated_response(serializer.data)

            serializer = SubmissionModelSerializer(
                qs, many=True, context={"request": request}
            )
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        request=SubmissionCreateSerializer,
        responses={201: SubmissionModelSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Crea una nueva submission (fase). Requiere usuario autenticado.",
    )
    def create(self, request):
        """Create new submission - validates input and delegates to repository."""
        serializer = SubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            repo = DjangoSubmissionRepository()
            created = repo.create_submission(**serializer.validated_data)
            return Response(
                SubmissionModelSerializer(created, context={"request": request}).data, 
                status=201
            )
        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        responses={200: SubmissionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Detalle de una submission. Requiere usuario autenticado.",
    )
    def retrieve(self, request, pk=None):
        """Get submission detail - delegates to service."""
        try:
            repo = DjangoSubmissionRepository()
            # Get the model directly from repository for serialization
            model = repo.detail_queryset().filter(id=pk).first()
            if not model:
                return Response({'error': 'Submission no encontrada.'}, status=404)
            
            return Response(SubmissionModelSerializer(model, context={"request": request}).data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Marca una submission como finalizada. Requiere usuario autenticado.",
    )
    def finalize(self, request, pk=None):
        """Finalize submission - delegates to service."""
        try:
            service = self._get_submission_service()
            updates = service.finalize_submission(pk)
            return Response({"mensaje": "Submission finalizada", **updates})
        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        responses={200: SubmissionModelSerializer},
        tags=["Submissions"],
        description="Detalle completo de una submission con respuestas. Requiere usuario autenticado.",
    )
    def enriched_detail(self, request, pk=None):
        """Get enriched submission detail with answers - delegates to service."""
        try:
            repo = DjangoSubmissionRepository()
            # Get the model directly from repository for serialization
            submission_model = repo.detail_queryset().filter(id=pk).first()
            if not submission_model:
                return Response({'error': 'Submission no encontrada.'}, status=404)
            
            return Response({
                'submission': SubmissionModelSerializer(submission_model, context={"request": request}).data,
                'answers': AnswerReadSerializer(submission_model.answers.all(), many=True, context={'request': request}).data,
            })
        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response({"error": str(e)}, status=500)





# ======================
# Historial — autenticado
# ======================
class HistorialReguladoresAPIView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("fecha_desde", OpenApiTypes.DATE, required=False),
            OpenApiParameter("fecha_hasta", OpenApiTypes.DATE, required=False),
            OpenApiParameter("solo_completados", OpenApiTypes.STR, required=False),
        ],
        responses={200: HistorialItemSerializer(many=True)},
        tags=["Historial"],
        description="Últimas fases por regulador_id. Requiere usuario autenticado.",
    )
    def get(self, request):
        p = request.query_params
        factory = get_service_factory()
        service = factory.create_history_service()
        items = service.list_history(
            fecha_desde=p.get("fecha_desde"),
            fecha_hasta=p.get("fecha_hasta"),
            solo_completados=p.get("solo_completados") in ("1", "true", "True"),
        )
        return Response(HistorialItemSerializer(items, many=True).data)


# ============================================
# Media protegida — autenticado (no público)
# ============================================
class MediaProtectedAPIView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("file_path", OpenApiTypes.STR, required=True)],
        description="Sirve archivos de MEDIA_ROOT controladamente. Requiere usuario autenticado.",
        responses={200: OpenApiTypes.BINARY, 404: OpenApiTypes.OBJECT},
        tags=["Media"],
    )
    def get(self, request, file_path):
        safe_root = os.path.abspath(settings.MEDIA_ROOT)
        abs_path = os.path.abspath(os.path.join(safe_root, file_path))
        if not abs_path.startswith(safe_root + os.sep):
            raise Http404("Ruta inválida")
        if not os.path.isfile(abs_path):
            raise Http404("Archivo no encontrado")
        return FileResponse(open(abs_path, "rb"))


# =====================================
# Catálogos — autenticado (no admin)
# =====================================
class ActorViewSet(viewsets.ViewSet):
    """
    GET /api/catalogos/actores/ — visible a usuarios autenticados.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        # Use repository pattern instead of direct model access
        from app.infrastructure.repositories import DjangoActorRepository
        repo = DjangoActorRepository()
        qs = repo.public_list(request.query_params)
        serializer = ActorModelSerializer(qs, many=True)
        return Response(serializer.data)


# =====================================
# Lista de cuestionarios — autenticado
# =====================================
class QuestionnaireListAPIView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: QuestionnaireListItemSerializer(many=True)},
        tags=["Cuestionario"],
        description="Lista de cuestionarios (id, título, versión, timezone). Requiere usuario autenticado.",
    )
    def get(self, request):
        qs = DjangoQuestionnaireRepository().list_minimal()
        return Response(QuestionnaireListItemSerializer(qs, many=True).data)


# =====================================
# Detalle de pregunta — autenticado
# =====================================
class QuestionDetailAPIView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: QuestionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Detalle de una pregunta por id. Requiere usuario autenticado.",
    )
    def get(self, request, id):
        try:
            # Usar el repositorio para obtener la pregunta
            from app.infrastructure.repositories import DjangoQuestionRepository
            repo = DjangoQuestionRepository()
            question_entity = repo.get(UUID(id))
            if not question_entity:
                return Response({"error": "Pregunta no encontrada."}, status=404)
            # Convertir la entidad de dominio a modelo para serialización
            q = QuestionModel.objects.get(id=question_entity.id)
            return Response(QuestionModelSerializer(q).data)
        except (ValueError, QuestionModel.DoesNotExist):
            return Response({"error": "Pregunta no encontrada."}, status=404)


# =====================================
# Admin (solo staff) — sin cambios
# =====================================
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AdminActorViewSet(viewsets.ViewSet):
    """
    /api/admin/actors/ — restringido a staff (panel administrativo).
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def list(self, request):
        from app.infrastructure.repositories import DjangoActorRepository
        repo = DjangoActorRepository()
        qs = repo.admin_queryset(request.query_params)
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = ActorModelSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ActorModelSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = ActorModelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        from app.infrastructure.models import Actor
        try:
            actor = Actor.objects.get(pk=pk)
            serializer = ActorModelSerializer(actor)
            return Response(serializer.data)
        except Actor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        from app.infrastructure.models import Actor
        try:
            actor = Actor.objects.get(pk=pk)
            serializer = ActorModelSerializer(actor, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Actor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        from app.infrastructure.models import Actor
        try:
            actor = Actor.objects.get(pk=pk)
            actor.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Actor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
