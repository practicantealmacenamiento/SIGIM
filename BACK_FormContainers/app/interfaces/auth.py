from __future__ import annotations

from typing import Optional, Tuple
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework import exceptions


class BearerOrTokenAuthentication(TokenAuthentication):
    """
    Autenticación compatible con:
      - Authorization: Bearer <token>
      - Authorization: Token <token>

    Notas:
    - Reutiliza la validación de DRF (TokenAuthentication.authenticate_credentials).
    - No introduce nuevas dependencias ni lógica de negocio.
    - Responde None si no hay encabezado Authorization o si el prefijo no coincide,
      permitiendo que otras autenticaciones (si existen) puedan actuar.
    """
    # Mantener 'Token' para compatibilidad con la implementación base.
    keyword = "Token"
    # Prefijos aceptados (case-insensitive).
    _SUPPORTED_PREFIXES = ("token", "bearer")

    def authenticate(self, request) -> Optional[Tuple[object, object]]:
        """
        Retorna (user, token) si el encabezado es válido, o None para ignorar
        y permitir a otros autenticadores manejar la solicitud.
        Lanza AuthenticationFailed para encabezados mal formados.
        """
        auth = get_authorization_header(request)
        if not auth:
            return None

        # auth es bytes; dividir por espacios
        parts = auth.split()
        if len(parts) == 0:
            return None
        if len(parts) == 1:
            # Prefijo sin credencial
            raise exceptions.AuthenticationFailed(
                _("Invalid token header. No credentials provided.")
            )
        if len(parts) > 2:
            # Demasiados segmentos => probablemente "Bearer a b"
            raise exceptions.AuthenticationFailed(
                _("Invalid token header. Token string should not contain spaces.")
            )

        try:
            prefix = parts[0].decode("utf-8").lower()
        except UnicodeError:
            raise exceptions.AuthenticationFailed(
                _("Invalid token header. Token prefix should not contain invalid characters.")
            )

        if prefix not in self._SUPPORTED_PREFIXES:
            # No es nuestro esquema; permitir a otros autenticadores
            return None

        try:
            token = parts[1].decode("utf-8")
        except UnicodeError:
            raise exceptions.AuthenticationFailed(
                _("Invalid token header. Token string should not contain invalid characters.")
            )

        if not token:
            raise exceptions.AuthenticationFailed(_("Invalid token header. No credentials provided."))

        # Delega en la implementación de DRF
        return self.authenticate_credentials(token)


# --------- Helpers de login (sin imports globales de DRF en import de módulo) ---------

def resolve_username_from_identifier(identifier: str) -> str:
    """
    Permite iniciar sesión con username o email (si existe un usuario con ese correo).
    Si no hay coincidencia por email, retorna el identificador original
    para que el backend de autenticación intente como username.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    ident = (identifier or "").strip()
    if "@" in ident:
        try:
            user = User.objects.get(email__iexact=ident)
            return user.get_username()
        except User.DoesNotExist:
            return ident
    return ident


def auth_login_issue_token(identifier: str, password: str):
    """
    Autentica por username/email + password y devuelve (user, token_key).
    Lanza ValueError si credenciales inválidas o usuario inactivo.

    Uso típico en una vista:
        user, key = auth_login_issue_token(data["identifier"], data["password"])
        return Response({"token": key, "user": build_user_payload(user)})
    """
    from django.contrib.auth import authenticate
    from rest_framework.authtoken.models import Token

    username = resolve_username_from_identifier(identifier)
    user = authenticate(username=username, password=password)
    if not user:
        raise ValueError("Credenciales inválidas.")
    if not getattr(user, "is_active", False):
        raise ValueError("Usuario inactivo.")

    token, _ = Token.objects.get_or_create(user=user)
    return user, token.key


def auth_logout_revoke_token(user) -> None:
    """
    Revoca (elimina) el token del usuario, si existe.
    Idempotente: no falla si no hay token.
    """
    from rest_framework.authtoken.models import Token

    if user and getattr(user, "is_authenticated", False):
        Token.objects.filter(user=user).delete()


def build_user_payload(user) -> dict:
    """
    Payload mínimo y seguro para exponer al frontend.
    No incluye datos sensibles ni permisos detallados.
    """
    return {
        "id": user.pk,
        "username": user.get_username(),
        "first_name": getattr(user, "first_name", "") or "",
        "last_name": getattr(user, "last_name", "") or "",
        "email": getattr(user, "email", "") or "",
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_superuser": bool(getattr(user, "is_superuser", False)),
    }


def build_auth_response(user, token_key: str) -> dict:
    """
    Estructura de respuesta estándar para endpoints de login.
    Centraliza el formato por si luego añadimos más campos (p.ej. expiración).
    """
    return {
        "token": token_key,
        "user": build_user_payload(user),
    }

