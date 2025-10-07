from __future__ import annotations

from typing import Optional, List
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db.models import Count, Prefetch, Q

from rest_framework import status, viewsets, mixins, serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

# Autenticación unificada
from .auth import BearerOrTokenAuthentication

# Infra / Serializers existentes en tu proyecto
from app.infrastructure.models import Questionnaire, Question, Choice, Actor
from app.infrastructure.serializers import (
    ActorModelSerializer,
    QuestionnaireListItemSerializer,
    QuestionnaireModelSerializer,
)

# =========================
# Paginación admin
# =========================
class AdminPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 200
    page_size = 20  # default


# =========================================================
# ADMIN — ACTORES
# =========================================================
class AdminActorViewSet(viewsets.ViewSet):
    """
    Gestión de actores (proveedores/transportistas/receptores) para admin.
    Serializadores manuales; sin lógica de negocio en la vista.
    """
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAdminUser]

    def _apply_filters(self, qs, request):
        """Aplica filtros de búsqueda por nombre/documento y por tipo."""
        raw_search = (
            request.query_params.get("search")
            or request.query_params.get("q")
            or request.query_params.get("term")
            or ""
        ).strip()
        tipo = (request.query_params.get("tipo") or "").strip().upper()

        if raw_search:
            qs = qs.filter(Q(nombre__icontains=raw_search) | Q(documento__icontains=raw_search))

        if tipo:
            valid_tipos = {c[0] for c in Actor.Tipo.choices}
            if tipo in valid_tipos:
                qs = qs.filter(tipo=tipo)

        return qs

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
    def list(self, request):
        qs = Actor.objects.all().order_by("nombre")
        qs = self._apply_filters(qs, request)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        data = ActorModelSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(tags=["admin/actors"], summary="Detalle actor")
    def retrieve(self, request, pk=None):
        try:
            obj = Actor.objects.get(pk=pk)
        except Actor.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ActorModelSerializer(obj).data)

    @extend_schema(tags=["admin/actors"], summary="Crear actor")
    def create(self, request):
        ser = ActorModelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = getattr(ser, "validated_data", request.data)

        obj = Actor.objects.create(
            nombre=data.get("nombre") or request.data.get("nombre") or "",
            tipo=data.get("tipo") or request.data.get("tipo") or Actor.Tipo.RECEPTOR,
            documento=data.get("documento") or request.data.get("documento") or request.data.get("nit"),
            activo=bool(data.get("activo", True)),
        )
        return Response(ActorModelSerializer(obj).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["admin/actors"], summary="Actualizar parcialmente actor (PATCH)")
    def partial_update(self, request, pk=None):
        try:
            obj = Actor.objects.get(pk=pk)
        except Actor.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)

        nombre = request.data.get("nombre", None)
        tipo = request.data.get("tipo", None)
        documento = request.data.get("documento", request.data.get("nit", None))
        activo = request.data.get("activo", None)

        if nombre is not None:
            obj.nombre = nombre
        if tipo is not None:
            obj.tipo = tipo
        if documento is not None:
            obj.documento = documento
        if activo is not None:
            obj.activo = bool(activo)

        obj.save()
        return Response(ActorModelSerializer(obj).data)

    @extend_schema(tags=["admin/actors"], summary="Eliminar actor")
    def destroy(self, request, pk=None):
        try:
            obj = Actor.objects.get(pk=pk)
        except Actor.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================================================
# ADMIN — USERS (utilidad básica)
# =========================================================
class AdminUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    is_staff = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def create(self, validated):
        User = get_user_model()
        pwd = validated.pop("password", None)
        if pwd:
            validated["password"] = make_password(pwd)
        return User.objects.create(**validated)

    def update(self, instance, validated):
        pwd = validated.pop("password", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if pwd:
            instance.password = make_password(pwd)
        instance.save()
        return instance


class AdminUserViewSet(viewsets.ViewSet):
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["admin/users"], summary="Listar usuarios")
    def list(self, request):
        User = get_user_model()
        return Response(AdminUserSerializer(User.objects.all(), many=True).data)

    @extend_schema(tags=["admin/users"], summary="Detalle usuario")
    def retrieve(self, request, pk=None):
        User = get_user_model()
        try:
            obj = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserSerializer(obj).data)

    @extend_schema(tags=["admin/users"], summary="Crear usuario")
    def create(self, request):
        ser = AdminUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = ser.save()
        return Response(AdminUserSerializer(instance).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["admin/users"], summary="Actualizar usuario (PUT)")
    def update(self, request, pk=None):
        User = get_user_model()
        try:
            obj = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        ser = AdminUserSerializer(obj, data=request.data)
        ser.is_valid(raise_exception=True)
        instance = ser.save()
        return Response(AdminUserSerializer(instance).data)

    @extend_schema(tags=["admin/users"], summary="Actualizar usuario (PATCH)")
    def partial_update(self, request, pk=None):
        User = get_user_model()
        try:
            obj = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        ser = AdminUserSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        instance = ser.save()
        return Response(AdminUserSerializer(instance).data)

    @extend_schema(tags=["admin/users"], summary="Eliminar usuario")
    def destroy(self, request, pk=None):
        User = get_user_model()
        try:
            obj = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

def _validate_question_type(t: Optional[str]) -> str:
    from app.infrastructure.models import Question as QModel
    allowed = {k for (k, _) in QModel.TYPE_CHOICES}
    t = (t or "text").strip()
    return t if t in allowed else "text"

def _normalize_semantic(s) -> str:
    from app.infrastructure.models import Question as QModel
    if s is None: return "none"
    s = (str(s) or "").strip().lower()
    if s in ("", "none"): return "none"
    allowed = {k for (k, _) in QModel.SEMANTIC_CHOICES}
    return s if s in allowed else "none"

# =========================================================
# ADMIN — CUESTIONARIOS
# =========================================================
class AdminQuestionnaireViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    """
    Listado + detalle + actualización parcial de cuestionarios y sus preguntas/opciones.
    - PUT y PATCH se tratan como parciales (no requiere enviar todo).
    - Sólo se sincronizan `questions`/`choices` si vienen y son arreglos.
    - `semantic_tag` NUNCA se guarda como NULL (se normaliza a "none" si viene vacío).
    """
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return (
            Questionnaire.objects
            .annotate(questions_count=Count("questions"))
            .only("id", "title", "version", "timezone")
            .order_by("title")
        )

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
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        term = (request.query_params.get("search") or "").strip()
        if term:
            qs = qs.filter(Q(title__icontains=term) | Q(version__icontains=term))
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        data = QuestionnaireListItemSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Detalle de un cuestionario (admin)",
        responses={200: QuestionnaireModelSerializer},
    )
    def retrieve(self, request, pk=None):
        qn = (
            Questionnaire.objects
            .filter(pk=pk)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=(
                        Question.objects
                        .order_by("order")
                        .prefetch_related(
                            Prefetch(
                                "choices",
                                queryset=Choice.objects.select_related("branch_to").order_by("text")
                            )
                        )
                    )
                )
            )
            .first()
        )
        if not qn:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionnaireModelSerializer(qn).data)
    
    # ------------------------
    # CREATE (POST)
    # ------------------------
    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Crear cuestionario (admin)",
        request=serializers.DictField,
        responses={201: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validación")},
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        payload = request.data or {}
        title = (payload.get("title") or "").strip()
        version = (payload.get("version") or "v1").strip()
        timezone = (payload.get("timezone") or "America/Bogota").strip()

        if not title:
            return Response({"title": "El título es obligatorio."}, status=400)

        qn = Questionnaire.objects.create(title=title, version=version or "v1", timezone=timezone or "America/Bogota")

        # Si vienen preguntas, crearlas
        if isinstance(payload.get("questions"), list):
            branch_links: list[tuple[Choice, Optional[str]]] = []
            for idx, qd in enumerate(payload["questions"]):
                text = (qd.get("text") or "").strip()
                if not text:
                    transaction.set_rollback(True)
                    return Response({"questions": f"La pregunta #{idx+1} requiere 'text'."}, status=400)
                qtype = _validate_question_type(qd.get("type"))
                required = bool(qd.get("required", False))
                order = int(qd.get("order") or idx)
                semantic_tag = _normalize_semantic(qd.get("semantic_tag"))
                file_mode = (qd.get("file_mode") or "image_only").strip()

                qobj = Question.objects.create(
                    questionnaire=qn,
                    text=text,
                    type=qtype,
                    required=required,
                    order=order,
                    file_mode=file_mode,
                    semantic_tag=semantic_tag,
                )

                # choices si vienen
                if isinstance(qd.get("choices"), list):
                    for cd in qd["choices"]:
                        ctext = (cd.get("text") or "").strip()
                        if not ctext:
                            transaction.set_rollback(True)
                            return Response({"choices": "Cada opción nueva debe tener 'text'."}, status=400)
                        branch_to = (cd.get("branch_to") or "").strip() or None
                        cobj = Choice.objects.create(question=qobj, text=ctext, branch_to=None)
                        branch_links.append((cobj, branch_to))

            # resolver branch_to luego de crear todas
            questions_index = {str(q.id): q for q in Questionnaire.objects.get(pk=qn.id).questions.all()}
            for cobj, target in branch_links:
                if target and target in questions_index:
                    cobj.branch_to = questions_index[target]
                    cobj.save()

        # responder
        fresh = (
            Questionnaire.objects.filter(pk=qn.id)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=Question.objects.order_by("order").prefetch_related(
                        Prefetch("choices", queryset=Choice.objects.select_related("branch_to").order_by("text"))
                    ),
                )
            ).first()
        )
        return Response(QuestionnaireModelSerializer(fresh).data, status=201)

    # ------------------------
    # UPDATE / PATCH (parciales)
    # ------------------------
    @extend_schema(tags=["admin/questionnaires"], summary="Actualizar (PUT parcial)", request=serializers.DictField,
                   responses={200: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validación")})
    def update(self, request, pk=None, *args, **kwargs):
        return self._upsert(pk=pk, payload=request.data, is_partial=True)

    @extend_schema(tags=["admin/questionnaires"], summary="Actualizar (PATCH)", request=serializers.DictField,
                   responses={200: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validación")})
    def partial_update(self, request, pk=None, *args, **kwargs):
        return self._upsert(pk=pk, payload=request.data, is_partial=True)

    @extend_schema(tags=["admin/questionnaires"], summary="Eliminar", responses={204: OpenApiResponse(description="OK")})
    def destroy(self, request, pk=None):
        try:
            obj = Questionnaire.objects.get(pk=pk)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        obj.delete()
        return Response(status=204)

    @transaction.atomic
    def _upsert(self, *, pk: str, payload: dict, is_partial: bool) -> Response:
        qn = (
            Questionnaire.objects.filter(pk=pk)
            .prefetch_related(Prefetch("questions", queryset=Question.objects.prefetch_related("choices").order_by("order")))
            .first()
        )
        if not qn:
            return Response({"detail": "No encontrado."}, status=404)

        # metadatos (sólo si vienen)
        if "title" in payload:
            title = (payload.get("title") or "").strip()
            if not title:
                return Response({"title": "El título no puede estar vacío."}, status=400)
            qn.title = title
        if "version" in payload:
            version = (payload.get("version") or "").strip()
            if not version:
                return Response({"version": "La versión no puede estar vacía."}, status=400)
            qn.version = version
        if "timezone" in payload:
            tz = (payload.get("timezone") or "").strip()
            if not tz:
                return Response({"timezone": "La zona horaria no puede estar vacía."}, status=400)
            qn.timezone = tz
        qn.save()

        # preguntas (sólo si llegan y son lista)
        if "questions" in payload and isinstance(payload.get("questions"), list):
            existing_qs = {str(q.id): q for q in qn.questions.all()}
            seen_qids: set[str] = set()
            branch_links: list[tuple[Choice, Optional[str]]] = []

            for qd in payload["questions"]:
                qid = (qd.get("id") or "").strip() or None
                text_present = "text" in qd
                raw_text = qd.get("text")
                text = (raw_text if raw_text is not None else "").strip()
                type_present = "type" in qd
                qtype = _validate_question_type(qd.get("type") if type_present else None)
                req_present = "required" in qd
                required = bool(qd.get("required")) if req_present else None
                order = None
                if "order" in qd:
                    try: order = int(qd.get("order"))
                    except: order = None
                sem_present = "semantic_tag" in qd
                semantic_tag = _normalize_semantic(qd.get("semantic_tag") if sem_present else None)
                fm_present = "file_mode" in qd
                file_mode = (qd.get("file_mode") or "").strip() if fm_present else None

                if qid and qid in existing_qs:
                    qobj = existing_qs[qid]
                    if text_present and raw_text is not None:
                        if not (is_partial and text == ""):
                            if text == "":
                                return Response({"questions": "Cada pregunta debe tener texto."}, status=400)
                            qobj.text = text
                    if type_present: qobj.type = qtype
                    if req_present:  qobj.required = bool(required)
                    if order is not None: qobj.order = order
                    if sem_present: qobj.semantic_tag = semantic_tag
                    if fm_present:  qobj.file_mode = file_mode or "image_only"
                    qobj.save()
                else:
                    if text == "":
                        return Response({"questions": "Cada pregunta nueva debe tener 'text'."}, status=400)
                    qobj = Question.objects.create(
                        questionnaire=qn,
                        text=text,
                        type=qtype,
                        required=bool(required) if req_present else False,
                        order=order if order is not None else 0,
                        file_mode=(file_mode or "image_only"),
                        semantic_tag=(semantic_tag or "none"),
                    )
                    qid = str(qobj.id)
                seen_qids.add(qid)

                # choices si vienen y son lista
                if "choices" in qd and isinstance(qd.get("choices"), list):
                    existing_cs = {str(c.id): c for c in qobj.choices.all()}
                    seen_cids: set[str] = set()
                    for cd in qd["choices"]:
                        cid = (cd.get("id") or "").strip() or None
                        ctext_present = "text" in cd
                        raw_ctext = cd.get("text")
                        ctext = (raw_ctext if raw_ctext is not None else "").strip()
                        branch_to = (cd.get("branch_to") or "").strip() or None

                        if cid and cid in existing_cs:
                            cobj = existing_cs[cid]
                            if ctext_present and raw_ctext is not None:
                                if not (is_partial and ctext == ""):
                                    if ctext == "":
                                        return Response({"choices": "Cada opción debe tener texto."}, status=400)
                                    cobj.text = ctext
                            cobj.branch_to = None
                            cobj.save()
                        else:
                            if ctext == "":
                                return Response({"choices": "Cada opción nueva debe tener 'text'."}, status=400)
                            cobj = Choice.objects.create(question=qobj, text=ctext, branch_to=None)
                            cid = str(cobj.id)
                        seen_cids.add(cid)
                        branch_links.append((cobj, branch_to))

                    # borrar las no vistas (sólo si mandaste lista)
                    for cid, cobj in list(existing_cs.items()):
                        if cid not in seen_cids:
                            cobj.delete()

            # borrar preguntas no vistas (sólo si mandaste lista)
            for qid, qobj in list(existing_qs.items()):
                if qid not in seen_qids:
                    qobj.delete()

            # resolver branch_to
            questions_index = {str(q.id): q for q in Questionnaire.objects.get(pk=qn.id).questions.all()}
            for cobj, target in branch_links:
                if target and target in questions_index:
                    cobj.branch_to = questions_index[target]
                    cobj.save()

        fresh = (
            Questionnaire.objects.filter(pk=qn.id)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=Question.objects.order_by("order").prefetch_related(
                        Prefetch("choices", queryset=Choice.objects.select_related("branch_to").order_by("text"))
                    ),
                )
            ).first()
        )
        return Response(QuestionnaireModelSerializer(fresh).data, status=200)

    # ------------------------
    # PUT/PATCH (parciales)
    # ------------------------
    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Actualizar cuestionario (PUT parcial)",
        request=serializers.DictField,
        responses={
            200: QuestionnaireModelSerializer,
            400: OpenApiResponse(description="Error de validación"),
            404: OpenApiResponse(description="No encontrado"),
        },
    )
    def update(self, request, pk=None, *args, **kwargs):
        return self._upsert(pk=pk, payload=request.data, is_partial=True)

    @extend_schema(
        tags=["admin/questionnaires"],
        summary="Actualizar parcialmente cuestionario (PATCH)",
        request=serializers.DictField,
        responses={
            200: QuestionnaireModelSerializer,
            400: OpenApiResponse(description="Error de validación"),
            404: OpenApiResponse(description="No encontrado"),
        },
    )
    def partial_update(self, request, pk=None, *args, **kwargs):
        return self._upsert(pk=pk, payload=request.data, is_partial=True)

    # =========================
    #   Soporte
    # =========================
    def _validate_question_type(self, t: Optional[str]) -> str:
        allowed = {k for (k, _) in Question.TYPE_CHOICES}
        t = (t or "text").strip()
        return t if t in allowed else "text"

    def _normalize_semantic(self, s) -> str:
        """
        Normaliza semantic_tag: nunca None (el modelo no permite NULL).
        """
        if s is None:
            return "none"
        s = (str(s) or "").strip().lower()
        if s in ("", "none"):
            return "none"
        allowed = {k for (k, _) in Question.SEMANTIC_CHOICES}
        return s if s in allowed else "none"

    @transaction.atomic
    def _upsert(self, *, pk: str, payload: dict, is_partial: bool) -> Response:
        qn = (
            Questionnaire.objects
            .filter(pk=pk)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=Question.objects.prefetch_related("choices").order_by("order")
                )
            )
            .first()
        )
        if not qn:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        @extend_schema(
            tags=["admin/questionnaires"],
            summary="Eliminar cuestionario (admin)",
            responses={204: OpenApiResponse(description="Eliminado"), 404: OpenApiResponse(description="No encontrado")},
        )
        def destroy(self, request, pk=None):
            try:
                obj = Questionnaire.objects.get(pk=pk)
            except Questionnaire.DoesNotExist:
                return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)

            # Cascada: elimina preguntas/choices asociados según FK on_delete
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # -------- Metadatos (sólo los campos presentes)
        errors = {}

        if "title" in payload:
            title = (payload.get("title") or "").strip()
            if title == "":
                errors["title"] = "El título no puede estar vacío."
            else:
                qn.title = title

        if "version" in payload:
            version = (payload.get("version") or "").strip()
            if version == "":
                errors["version"] = "La versión no puede estar vacía."
            else:
                qn.version = version

        if "timezone" in payload:
            tz = (payload.get("timezone") or "").strip()
            if tz == "":
                errors["timezone"] = "La zona horaria no puede estar vacía."
            else:
                qn.timezone = tz

        if errors:
            return Response(errors, status=400)

        qn.save()

        # -------- Preguntas (sólo si vienen y son lista)
        if "questions" in payload and isinstance(payload.get("questions"), list):
            incoming_questions: List[dict] = payload.get("questions") or []
            existing_qs = {str(q.id): q for q in qn.questions.all()}

            seen_question_ids: set[str] = set()
            choice_branch_map: List[tuple[Choice, Optional[str]]] = []

            for qd in incoming_questions:
                qid = (qd.get("id") or "").strip() or None

                # Presencia de campos
                text_is_set = "text" in qd
                type_is_set = "type" in qd
                req_is_set = "required" in qd
                order_is_set = "order" in qd
                sem_is_set = "semantic_tag" in qd
                fm_is_set = "file_mode" in qd

                raw_text = qd.get("text")
                text = (raw_text if raw_text is not None else "").strip()
                qtype = self._validate_question_type(qd.get("type") if type_is_set else None)
                required = bool(qd.get("required")) if req_is_set else None

                order = None
                if order_is_set:
                    try:
                        order = int(qd.get("order"))
                    except Exception:
                        order = None

                semantic_tag = self._normalize_semantic(qd.get("semantic_tag") if sem_is_set else None)
                file_mode = (qd.get("file_mode") or "").strip() if fm_is_set else None

                if qid and qid in existing_qs:
                    # UPDATE parcial
                    qobj = existing_qs[qid]

                    if text_is_set and raw_text is not None:
                        if not (is_partial and text == ""):
                            if text == "":
                                return Response({"questions": "Cada pregunta debe tener texto."}, status=400)
                            qobj.text = text

                    if type_is_set:
                        qobj.type = qtype
                    if req_is_set:
                        qobj.required = bool(required)
                    if order is not None:
                        qobj.order = order
                    if sem_is_set:
                        qobj.semantic_tag = semantic_tag  # "none" seguro
                    if fm_is_set:
                        qobj.file_mode = file_mode or "image_only"

                    qobj.save()
                else:
                    # CREATE: requiere text
                    if text == "":
                        return Response({"questions": "Cada pregunta nueva debe tener 'text'."}, status=400)

                    qobj = Question.objects.create(
                        questionnaire=qn,
                        text=text,
                        type=qtype,
                        required=bool(required) if req_is_set else False,
                        order=order if order is not None else 0,
                        file_mode=(file_mode or "image_only"),
                        semantic_tag=(semantic_tag or "none"),
                    )
                    qid = str(qobj.id)

                seen_question_ids.add(qid)

                # Choices: sólo si vienen y son lista
                if "choices" in qd and isinstance(qd.get("choices"), list):
                    incoming_choices = qd.get("choices") or []
                    existing_choices = {str(c.id): c for c in qobj.choices.all()}
                    seen_choice_ids: set[str] = set()

                    for cd in incoming_choices:
                        cid = (cd.get("id") or "").strip() or None

                        ctext_is_set = "text" in cd
                        raw_ctext = cd.get("text")
                        ctext = (raw_ctext if raw_ctext is not None else "").strip()

                        branch_to = (cd.get("branch_to") or "").strip() or None

                        if cid and cid in existing_choices:
                            cobj = existing_choices[cid]

                            if ctext_is_set and raw_ctext is not None:
                                if not (is_partial and ctext == ""):
                                    if ctext == "":
                                        return Response({"choices": "Cada opción debe tener texto."}, status=400)
                                    cobj.text = ctext

                            # branch_to se resuelve en 2a pasada
                            cobj.branch_to = None
                            cobj.save()
                        else:
                            # CREATE: requiere text
                            if ctext == "":
                                return Response({"choices": "Cada opción nueva debe tener 'text'."}, status=400)
                            cobj = Choice.objects.create(question=qobj, text=ctext, branch_to=None)
                            cid = str(cobj.id)

                        seen_choice_ids.add(cid)
                        choice_branch_map.append((cobj, branch_to))

                    # Borrar choices no vistos (sólo si mandaste lista)
                    for cid, cobj in list(existing_choices.items()):
                        if cid not in seen_choice_ids:
                            cobj.delete()

            # Borrar preguntas no vistas (sólo si mandaste lista)
            for qid, qobj in list(existing_qs.items()):
                if qid not in seen_question_ids:
                    qobj.delete()

            # Segunda pasada: branch_to (una vez existen todas)
            questions_index = {str(q.id): q for q in Questionnaire.objects.get(pk=qn.id).questions.all()}
            for cobj, target_id in choice_branch_map:
                if target_id and target_id in questions_index:
                    cobj.branch_to = questions_index[target_id]
                    cobj.save()

        # Responder con el detalle fresco
        fresh = (
            Questionnaire.objects
            .filter(pk=qn.id)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=(
                        Question.objects
                        .order_by("order")
                        .prefetch_related(
                            Prefetch("choices", queryset=Choice.objects.select_related("branch_to").order_by("text"))
                        )
                    )
                )
            )
            .first()
        )
        return Response(QuestionnaireModelSerializer(fresh).data, status=200)
