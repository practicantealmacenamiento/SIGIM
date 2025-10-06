from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework import exceptions

class BearerOrTokenAuthentication(TokenAuthentication):
    """
    Acepta:
      - Authorization: Bearer <token>
      - Authorization: Token <token>
    Reutiliza DRF TokenAuthentication para validar credenciales.
    """
    keyword = "Token"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            return None
        if len(auth) == 1:
            raise exceptions.AuthenticationFailed(_("Invalid token header. No credentials provided."))
        if len(auth) > 2:
            raise exceptions.AuthenticationFailed(_("Invalid token header. Token string should not contain spaces."))

        prefix = auth[0].decode("utf-8").lower()
        if prefix not in ("token", "bearer"):
            return None

        try:
            token = auth[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed(_("Invalid token header. Token string should not contain invalid characters."))

        return self.authenticate_credentials(token)


# --------- Helpers de login sin dependencias de DRF en import de módulo ---------

def resolve_username_from_identifier(identifier: str) -> str:
    """Permite iniciar sesión con username o email (si existe)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    ident = (identifier or "").strip()
    if "@" in ident:
        try:
            user = User.objects.get(email__iexact=ident)
            return user.get_username()
        except User.DoesNotExist:
            return ident  # intenta como username igualmente
    return ident


def auth_login_issue_token(identifier: str, password: str):
    """
    Autentica por username/email + password y devuelve (user, token_key).
    Lanza ValueError si credenciales inválidas o usuario inactivo.
    """
    from django.contrib.auth import authenticate, get_user_model
    from rest_framework.authtoken.models import Token

    username = resolve_username_from_identifier(identifier)
    user = authenticate(username=username, password=password)
    if not user:
        raise ValueError("Credenciales inválidas.")
    if not user.is_active:
        raise ValueError("Usuario inactivo.")

    token, _ = Token.objects.get_or_create(user=user)
    return user, token.key


def build_user_payload(user):
    """Pequeño payload para el frontend."""
    return {
        "id": user.pk,
        "username": user.get_username(),
        "first_name": getattr(user, "first_name", "") or "",
        "last_name": getattr(user, "last_name", "") or "",
        "email": getattr(user, "email", "") or "",
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_superuser": bool(getattr(user, "is_superuser", False)),
    }
