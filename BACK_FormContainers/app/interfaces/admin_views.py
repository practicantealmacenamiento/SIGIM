from __future__ import annotations

from typing import Optional, List, Tuple
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db.models import Count, Prefetch, Q, F, Max

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
# Utilidades locales
# =========================
def _validate_question_type(t: Optional[str]) -> str:
    allowed = {k for (k, _) in Question.TYPE_CHOICES}
    t = (t or "text").strip()
    return t if t in allowed else "text"

def _normalize_semantic(s) -> str:
    if s is None:
        return "none"
    s = (str(s) or "").strip().lower()
    if s in ("", "none"):
        return "none"
    allowed = {k for (k, _) in Question.SEMANTIC_CHOICES}
    return s if s in allowed else "none"


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


# =========================================================
# ADMIN — CUESTIONARIOS
# =========================================================
class AdminQuestionnaireViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    """
    Listado + detalle + creación y actualización parcial de cuestionarios con sus preguntas/opciones.
    - PUT y PATCH se tratan como parciales (no requiere enviar todo).
    - Se resuelve "order" evitando colisiones con un SHIFT en dos fases (OFFSET grande).
    - `semantic_tag` nunca se persiste como NULL (se normaliza a "none").
    """
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAdminUser]

    BIG_OFFSET = 1_000_000  # para evitar colisiones temporales en UNIQUE(questionnaire_id, order)

    # ---------- Helper para desplazar bloques de orden ----------
    def _shift_range(self, *, qn: Questionnaire, start: int, end: Optional[int], direction: str, exclude_id: Optional[str] = None) -> None:
        """
        Desplaza en +1 (direction='up') o -1 (direction='down') el bloque [start..end]
        (si end es None, aplica a [start..∞)).
        Hace el desplazamiento en DOS FASES con un OFFSET grande para no violar la UNIQUE.
        """
        qs = Question.objects.filter(questionnaire=qn, order__gte=start)
        if end is not None:
            qs = qs.filter(order__lte=end)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        if not qs.exists():
            return

        OFF = self.BIG_OFFSET
        # Fase 1: alejar
        qs.update(order=F("order") + OFF)
        # Fase 2: dejar en su valor final
        if direction == "up":
            # queremos +1 neto: (order+OFF) - (OFF-1) = order + 1
            qs.update(order=F("order") - (OFF - 1))
        else:
            # queremos -1 neto: (order+OFF) - (OFF+1) = order - 1
            qs.update(order=F("order") - (OFF + 1))

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
            branch_links: List[Tuple[Choice, Optional[str]]] = []
            for idx, qd in enumerate(payload["questions"]):
                text = (qd.get("text") or "").strip()
                if not text:
                    transaction.set_rollback(True)
                    return Response({"questions": f"La pregunta #{idx+1} requiere 'text'."}, status=400)

                qtype = _validate_question_type(qd.get("type"))
                required = bool(qd.get("required", False))
                file_mode = (qd.get("file_mode") or "image_only").strip()
                semantic_tag = _normalize_semantic(qd.get("semantic_tag"))

                # --- ORDEN con SHIFT seguro ---
                incoming_order = qd.get("order")
                try:
                    new_order = int(incoming_order) if incoming_order is not None else None
                except Exception:
                    new_order = None

                if new_order is None:
                    max_order = qn.questions.aggregate(m=Max("order"))["m"]
                    safe_order = (max_order if max_order is not None else -1) + 1
                else:
                    # Desplaza todo lo >= new_order en +1 (dos fases)
                    self._shift_range(qn=qn, start=new_order, end=None, direction="up")
                    safe_order = new_order

                qobj = Question.objects.create(
                    questionnaire=qn,
                    text=text,
                    type=qtype,
                    required=required,
                    order=safe_order,
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
    @extend_schema(
        tags=["admin/questionnaires"], summary="Actualizar (PUT parcial)", request=serializers.DictField,
        responses={200: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validación")}
    )
    def update(self, request, pk=None, *args, **kwargs):
        return self._upsert(pk=pk, payload=request.data, is_partial=True)

    @extend_schema(
        tags=["admin/questionnaires"], summary="Actualizar (PATCH)", request=serializers.DictField,
        responses={200: QuestionnaireModelSerializer, 400: OpenApiResponse(description="Error de validación")}
    )
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

    # =========================
    #   Upsert con SHIFT de orden
    # =========================
    @transaction.atomic
    def _upsert(self, *, pk: str, payload: dict, is_partial: bool) -> Response:
        qn = (
            Questionnaire.objects.filter(pk=pk)
            .prefetch_related(Prefetch("questions", queryset=Question.objects.prefetch_related("choices").order_by("order")))
            .first()
        )
        if not qn:
            return Response({"detail": "No encontrado."}, status=404)

        # -------- Metadatos (sólo presentes)
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

        # -------- Preguntas (sólo si vienen y son lista)
        if "questions" in payload and isinstance(payload.get("questions"), list):
            existing_qs = {str(q.id): q for q in qn.questions.all()}
            seen_qids: set[str] = set()
            branch_links: List[Tuple[Choice, Optional[str]]] = []

            for qd in payload["questions"]:
                qid = (qd.get("id") or "").strip() or None

                # Presencia
                text_present = "text" in qd
                type_present = "type" in qd
                req_present = "required" in qd
                order_present = "order" in qd
                sem_present = "semantic_tag" in qd
                fm_present = "file_mode" in qd

                # Valores normalizados
                raw_text = qd.get("text")
                text = (raw_text if raw_text is not None else "").strip()
                qtype = _validate_question_type(qd.get("type") if type_present else None)
                required = bool(qd.get("required")) if req_present else None
                semantic_tag = _normalize_semantic(qd.get("semantic_tag") if sem_present else None)
                file_mode = (qd.get("file_mode") or "").strip() if fm_present else None

                # Orden entrante
                new_order: Optional[int] = None
                if order_present:
                    try:
                        new_order = int(qd.get("order"))
                    except Exception:
                        new_order = None

                if qid and qid in existing_qs:
                    # === UPDATE con resolución de colisiones ===
                    qobj = existing_qs[qid]
                    old_order = qobj.order

                    if text_present and raw_text is not None:
                        if not (is_partial and text == ""):
                            if text == "":
                                return Response({"questions": "Cada pregunta debe tener texto."}, status=400)
                            qobj.text = text
                    if type_present:
                        qobj.type = qtype
                    if req_present:
                        qobj.required = bool(required)
                    if sem_present:
                        qobj.semantic_tag = semantic_tag
                    if fm_present:
                        qobj.file_mode = file_mode or "image_only"

                    # Si cambia de posición, desplazo el bloque afectado y luego asigno el nuevo order
                    if new_order is not None and new_order != old_order:
                        if new_order < old_order:
                            # Sube: incrementa [new_order .. old_order-1]
                            self._shift_range(qn=qn, start=new_order, end=old_order - 1, direction="up", exclude_id=qobj.id)
                        else:
                            # Baja: decrementa [old_order+1 .. new_order]
                            self._shift_range(qn=qn, start=old_order + 1, end=new_order, direction="down", exclude_id=qobj.id)
                        qobj.order = new_order

                    qobj.save()

                else:
                    # === CREATE con resolución de colisiones ===
                    if text == "":
                        return Response({"questions": "Cada pregunta nueva debe tener 'text'."}, status=400)

                    # Determinar order seguro
                    if new_order is None:
                        max_order = qn.questions.aggregate(m=Max("order"))["m"]
                        safe_order = (max_order if max_order is not None else -1) + 1
                    else:
                        # Empuja todo lo >= new_order en +1
                        self._shift_range(qn=qn, start=new_order, end=None, direction="up")
                        safe_order = new_order

                    qobj = Question.objects.create(
                        questionnaire=qn,
                        text=text,
                        type=qtype,
                        required=bool(required) if req_present else False,
                        order=safe_order,
                        file_mode=(file_mode or "image_only"),
                        semantic_tag=(semantic_tag or "none"),
                    )
                    qid = str(qobj.id)

                seen_qids.add(qid)

                # Choices si vienen
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
                            cobj.branch_to = None  # se resuelve luego
                            cobj.save()
                        else:
                            if ctext == "":
                                return Response({"choices": "Cada opción nueva debe tener 'text'."}, status=400)
                            cobj = Choice.objects.create(question=qobj, text=ctext, branch_to=None)
                            cid = str(cobj.id)

                        seen_cids.add(cid)
                        branch_links.append((cobj, branch_to))

                    # borrar no vistas
                    for cid, cobj in list(existing_cs.items()):
                        if cid not in seen_cids:
                            cobj.delete()

            # borrar preguntas no vistas
            for qid, qobj in list(existing_qs.items()):
                if qid not in seen_qids:
                    qobj.delete()

            # Resolver branch_to (ya existen todas)
            questions_index = {str(q.id): q for q in Questionnaire.objects.get(pk=qn.id).questions.all()}
            for cobj, target in branch_links:
                if target and target in questions_index:
                    cobj.branch_to = questions_index[target]
                    cobj.save()

        # Responder con el detalle fresco
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
