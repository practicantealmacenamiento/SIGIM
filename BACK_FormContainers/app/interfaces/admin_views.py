from __future__ import annotations

from dataclasses import replace
from typing import List, Dict
from uuid import UUID, uuid4
from urllib.parse import urlsplit

# Django / DRF
from rest_framework.authentication import TokenAuthentication, SessionAuthentication, get_authorization_header
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth import logout as django_logout
from django.db import transaction, IntegrityError
from django.conf import settings
from django.middleware.csrf import get_token

from rest_framework import mixins, viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated  # ⬅️ IsAuthenticated agregado
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

# Tu capa de infraestructura / dominio
from app.interfaces.entity_serializers import DomainQuestionnaireSerializer
from app.infrastructure.factories import get_service_factory
from app.infrastructure.repositories import DjangoQuestionnaireRepository
from app.domain.entities import Questionnaire as DQn, Question as DQ, Choice as DC


# ----------------- Helpers de conversión dominio -----------------
class BearerOrTokenAuthentication(TokenAuthentication):
    """
    Permite Authorization: "Token <key>" (DRF) o "Bearer <key>" (estándar OAuth).
    Normalizamos a "Token" para que TokenAuthentication funcione sin cambios.
    """
    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if auth and auth[0].lower() == b"bearer" and len(auth) == 2:
            request.META["HTTP_AUTHORIZATION"] = b"Token " + auth[1]
        return super().authenticate(request)

def _qn_repo() -> DjangoQuestionnaireRepository:
    return DjangoQuestionnaireRepository()

def _to_domain_choice(d: dict) -> DC:
    return DC(id=d["id"], text=d["text"], branch_to=d.get("branch_to"))

def _to_domain_question(d: dict) -> DQ:
    choices = tuple(_to_domain_choice(c) for c in (d.get("choices") or []))
    return DQ(
        id=d["id"],
        text=d["text"],
        type=d["type"],
        required=d["required"],
        order=d["order"],
        choices=choices,
        semantic_tag=d.get("semantic_tag"),
        file_mode=d.get("file_mode"),
    )

def _to_domain_questionnaire(d: dict) -> DQn:
    questions = tuple(_to_domain_question(q) for q in (d.get("questions") or []))
    return DQn(
        id=d["id"],
        title=d["title"],
        version=d["version"],
        timezone=d["timezone"],
        questions=questions,
    )

class AdminLogoutAPIView(APIView):
    """
    Cierra la sesión de servidor (sessionid) y limpia cookies de UI.
    No es un endpoint sensible: si no hay sesión, responde ok igual.
    """
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        # cierra sesión de servidor si existía
        try:
            django_logout(request)
        except Exception:
            pass

        resp = Response({"ok": True}, status=status.HTTP_200_OK)

        # borra cookies comunes (ajusta domain/secure según tu settings)
        cookie_domain = getattr(settings, "SESSION_COOKIE_DOMAIN", None)
        cookie_secure = getattr(settings, "SESSION_COOKIE_SECURE", False)
        cookie_samesite = getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax")

        resp.delete_cookie("sessionid", path="/", domain=cookie_domain, samesite=cookie_samesite)
        resp.delete_cookie("auth_token", path="/", domain=cookie_domain, samesite=cookie_samesite)
        resp.set_cookie("is_staff", "0", path="/", domain=cookie_domain, samesite=cookie_samesite, secure=cookie_secure)

        # refresca CSRF para siguientes formularios anónimos (opcional)
        csrf_name = getattr(settings, "CSRF_COOKIE_NAME", "csrftoken")
        resp.set_cookie(
            key=csrf_name,
            value=get_token(request),
            httponly=False,
            samesite=getattr(settings, "CSRF_COOKIE_SAMESITE", "Lax"),
            secure=getattr(settings, "CSRF_COOKIE_SECURE", False),
            domain=cookie_domain,
            path="/",
        )
        return resp
# ============================
# ADMIN QUESTIONNAIRES
# ============================

class AdminQuestionnaireViewSet(viewsets.ViewSet):
    """
    - GET    /api/admin/questionnaires/
    - GET    /api/admin/questionnaires/{id}/
    - POST   /api/admin/questionnaires/
    - PUT    /api/admin/questionnaires/{id}/
    - POST   /api/admin/questionnaires/upsert/
    - POST   /api/admin/questionnaires/{id}/reorder/
    - POST   /api/admin/questionnaires/{id}/duplicate/
    - DELETE /api/admin/questionnaires/{id}/
    """
    # Token primero, luego sesión (evita 403 cuando sí llega Authorization)
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    # LIST
    def list(self, request):
        repo = _qn_repo()
        items = []
        for q in repo.list_all():
            items.append({
                "id": str(q.id),
                "title": q.title,
                "version": q.version,
                "questions": len(q.questions),
            })
        return Response(items, status=status.HTTP_200_OK)

    # RETRIEVE
    def retrieve(self, request, pk=None):
        repo = _qn_repo()
        qn = repo.get_by_id(UUID(pk))
        if not qn:
            return Response({"detail": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
        data = DomainQuestionnaireSerializer(qn).data
        return Response(data, status=status.HTTP_200_OK)

    # CREATE
    @transaction.atomic
    def create(self, request):
        s = DomainQuestionnaireSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dq = _to_domain_questionnaire(s.validated_data)
        repo = _qn_repo()
        try:
            saved = repo.save(dq)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = DomainQuestionnaireSerializer(saved).data
        return Response(out, status=status.HTTP_201_CREATED)

    # UPDATE
    @transaction.atomic
    def update(self, request, pk=None):
        data = dict(request.data) if hasattr(request.data, "items") else request.data
        data = {**data, "id": str(pk)}
        s = DomainQuestionnaireSerializer(data=data)
        s.is_valid(raise_exception=True)
        dq = _to_domain_questionnaire(s.validated_data)
        repo = _qn_repo()
        try:
            saved = repo.save(dq)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = DomainQuestionnaireSerializer(saved).data
        return Response(out, status=status.HTTP_200_OK)

    # UPSERT (legacy)
    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        s = DomainQuestionnaireSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dq = _to_domain_questionnaire(s.validated_data)
        repo = _qn_repo()
        try:
            saved = repo.save(dq)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = DomainQuestionnaireSerializer(saved).data
        return Response(out, status=status.HTTP_200_OK)

    # REORDER
    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="reorder")
    def reorder(self, request, pk=None):
        order_ids: List[str] = list(request.data.get("order") or [])
        if not order_ids:
            return Response({"detail": "Falta 'order' con lista de UUIDs."}, status=status.HTTP_400_BAD_REQUEST)

        repo = _qn_repo()
        qn = repo.get_by_id(UUID(pk))
        if not qn:
            return Response({"detail": "Cuestionario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        current_ids = {str(q.id) for q in qn.questions}
        incoming_ids = set(order_ids)
        if current_ids != incoming_ids:
            return Response(
                {"detail": "La lista 'order' debe contener exactamente los UUIDs de las preguntas actuales."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        index_by_id: Dict[str, int] = {qid: idx for idx, qid in enumerate(order_ids, start=1)}
        new_questions = tuple(replace(q, order=index_by_id[str(q.id)]) for q in qn.questions)
        new_questions = tuple(sorted(new_questions, key=lambda x: x.order))

        updated = DQn(
            id=qn.id,
            title=qn.title,
            version=qn.version,
            timezone=qn.timezone,
            questions=new_questions,
        )
        saved = repo.save(updated)
        return Response({"ok": True, "questions": len(saved.questions)}, status=status.HTTP_200_OK)

    # DUPLICATE
    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        repo = _qn_repo()
        qn = repo.get_by_id(UUID(pk))
        if not qn:
            return Response({"detail": "Cuestionario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        new_qn_id = uuid4()
        new_version = request.data.get("version") or f"{qn.version} (copy)"

        old_to_new_q: Dict[UUID, UUID] = {}
        new_questions: List[DQ] = []
        for i, q in enumerate(sorted(qn.questions, key=lambda x: x.order), start=1):
            new_q_id = uuid4()
            old_to_new_q[q.id] = new_q_id
            new_questions.append(
                DQ(
                    id=new_q_id,
                    text=q.text,
                    type=q.type,
                    required=q.required,
                    order=i,
                    choices=tuple(),
                    semantic_tag=q.semantic_tag,
                    file_mode=q.file_mode,
                )
            )

        by_new_id = {q.id: q for q in new_questions}
        final_questions: List[DQ] = []
        for old_q in sorted(qn.questions, key=lambda x: x.order):
            nq = by_new_id[old_to_new_q[old_q.id]]
            new_choices: List[DC] = []
            for c in old_q.choices:
                new_branch = old_to_new_q.get(c.branch_to) if c.branch_to else None
                new_choices.append(DC(id=uuid4(), text=c.text, branch_to=new_branch))
            final_questions.append(replace(nq, choices=tuple(new_choices)))

        new_dq = DQn(
            id=new_qn_id,
            title=qn.title,
            version=new_version,
            timezone=qn.timezone,
            questions=tuple(final_questions),
        )

        try:
            saved = repo.save(new_dq)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"id": str(saved.id)}, status=status.HTTP_201_CREATED)

    # DELETE
    def destroy(self, request, pk=None):
        # Use service layer instead of direct model access
        factory = get_service_factory()
        # Get the questionnaire repository through the factory
        questionnaire_repo = factory._get_questionnaire_repository()
        try:
            deleted = questionnaire_repo.delete(UUID(pk))
        except Exception:
            deleted = False
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


# ============================
# ADMIN USERS (CRUD mínimo)
# ============================

UserModel = get_user_model()

class AdminUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    email = serializers.EmailField(allow_blank=True, required=False)
    is_staff = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(write_only=True, required=True)

    def create(self, validated_data):
        pwd = validated_data.pop("password")
        user = UserModel(**validated_data)
        user.set_password(pwd)
        user.save()
        return user

    def update(self, instance, validated_data):
        pwd = validated_data.pop("password", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if pwd:
            instance.set_password(pwd)
        instance.save()
        return instance


class AdminUserViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    queryset = UserModel.objects.all().order_by("username")
    serializer_class = AdminUserSerializer
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


# ============================
# LOGIN ADMIN (sesión + token DRF) + WHOAMI de diagnóstico
# ============================

class AdminLoginAPIView(APIView):
    """
    - Acepta {username,password} o {email,password}
    - Inicia sesión (cookie de sesión)
    - Devuelve token DRF (para Authorization: Token <key>)
    - Emite cookie CSRF (útil para no-GET con sesión)
    """
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username") or request.data.get("email") or ""
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"detail": "username/email y password requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        if "@" in username:
            try:
                u = User.objects.get(email__iexact=username)
                username = u.get_username()
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({"detail": "Credenciales inválidas."}, status=status.HTTP_400_BAD_REQUEST)

        # Crea sesión
        login(request, user)

        # Token DRF
        token, _ = Token.objects.get_or_create(user=user)

        # Respuesta + CSRF cookie
        resp = Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.get_username(),
                "email": user.email,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            }
        }, status=status.HTTP_200_OK)

        # Emite CSRF cookie (para SPA con SessionAuth)
        csrf_name = getattr(settings, "CSRF_COOKIE_NAME", "csrftoken")
        csrf_val = get_token(request)
        resp.set_cookie(
            key=csrf_name,
            value=csrf_val,
            httponly=False,
            samesite=getattr(settings, "CSRF_COOKIE_SAMESITE", "Lax"),
            secure=getattr(settings, "CSRF_COOKIE_SECURE", False),
            domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None),
            path="/",
        )

        resp.set_cookie(
            key="is_staff",
            value="1" if user.is_staff else "0",
            httponly=False,
            samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
            secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
            domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None),
            path="/",
        )
        resp.set_cookie(
            key="auth_username",
            value=user.get_username() or "",
            httponly=False,
            samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
            secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
            domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None),
            path="/",
        )
        # (Opcional) dejar el token accesible a JS para que el primer whoami
        # tenga Authorization incluso si LS aún no fue escrito:
        resp.set_cookie(
            key="auth_token",
            value=token.key,
            httponly=False,
            samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
            secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
            domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None),
            path="/",
        )

        return resp


class AdminWhoAmI(APIView):
    """
    Responde SIEMPRE 200. Nunca redirige.
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        u = request.user if request.user.is_authenticated else None
        return Response({
            "is_authenticated": bool(u),
            "username": (u.get_username() if u else ""),
            "is_staff": bool(u and getattr(u, "is_staff", False)),
        })
