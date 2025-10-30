"""Permisos personalizados para proteger endpoints de escritura."""

from __future__ import annotations

import hmac
import os
from typing import Optional

import environ
from rest_framework.permissions import SAFE_METHODS, BasePermission

env = environ.Env()
env.read_env(env_file=os.environ.get("ENV_FILE", ".env"))


class TokenRequiredForWrite(BasePermission):
    """Permite lectura libre y exige token para operaciones de escritura."""

    message = "Credenciales no validas o ausentes."

    def _expected_token(self) -> Optional[str]:
        """Obtiene el token esperado desde variables de entorno."""

        return env("API_SECRET_TOKEN", default=None)

    def _provided_token(self, request) -> Optional[str]:
        """Extrae el token aportado en headers Authorization o X-API-KEY."""

        auth_header = request.headers.get("Authorization", "")
        if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()

        api_key = request.headers.get("X-API-KEY")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

        return None

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if request.method in SAFE_METHODS:
            return True

        expected = self._expected_token()
        provided = self._provided_token(request)

        if not expected:
            self.message = "Servidor sin API_SECRET_TOKEN configurado."
            return False

        if not provided:
            self.message = "Falta Authorization: Bearer <token> o X-API-KEY."
            return False

        if hmac.compare_digest(provided, expected):
            return True

        self.message = "Token invalido."
        return False


__all__ = ["TokenRequiredForWrite"]
