from rest_framework.permissions import BasePermission, SAFE_METHODS
import os
import hmac
import environ

# Cargar variables de entorno (si existe .env)
env = environ.Env()
env.read_env(env_file=os.environ.get("ENV_FILE", ".env"))

class TokenRequiredForWrite(BasePermission):
    """
    Permite métodos seguros (GET/HEAD/OPTIONS) sin restricción.
    Requiere token para métodos de escritura (POST/PUT/PATCH/DELETE).
    Soporta 'Authorization: Bearer <token>' o 'X-API-KEY: <token>'.
    """
    message = "Credenciales no válidas o ausentes."

    def _expected_token(self) -> str | None:
        # No revienta si falta; lo manejamos explícitamente
        return env("API_SECRET_TOKEN", default=None)

    def _provided_token(self, request) -> str | None:
        # Authorization: Bearer <token>
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        # Fallback: X-API-KEY: <token>
        api_key = request.headers.get("X-API-KEY")
        if api_key:
            return api_key.strip()
        return None

    def has_permission(self, request, view) -> bool:
        # GET/HEAD/OPTIONS libres
        if request.method in SAFE_METHODS:
            return True

        expected = self._expected_token()
        provided = self._provided_token(request)

        if not expected:
            # Mejor negar explícitamente que dejar el backend abierto por falta de config
            self.message = "Servidor sin API_SECRET_TOKEN configurado."
            return False

        if not provided:
            self.message = "Falta Authorization: Bearer <token> o X-API-KEY."
            return False

        if hmac.compare_digest(provided, expected):
            return True

        self.message = "Token inválido."
        return False