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
# -*- coding: utf-8 -*-
"""
Permiso DRF que exige token de API para métodos de escritura.

Comportamiento:
- Métodos seguros (GET/HEAD/OPTIONS): permitidos sin autenticación.
- Métodos de escritura (POST/PUT/PATCH/DELETE): requieren un token válido.
- Fuentes del token:
    * Cabecera `Authorization: Bearer <token>`
    * Cabecera `X-API-KEY: <token>`

El token esperado se obtiene de la variable de entorno `API_SECRET_TOKEN`.
Si no está configurada, se deniega el acceso a métodos de escritura.
"""

from __future__ import annotations

import hmac
import os
from typing import Optional

import environ
from rest_framework.permissions import SAFE_METHODS, BasePermission

# Carga de entorno (.env opcional)
env = environ.Env()
env.read_env(env_file=os.environ.get("ENV_FILE", ".env"))

__all__ = ["TokenRequiredForWrite"]


class TokenRequiredForWrite(BasePermission):
    """
    Permite métodos seguros sin restricción y exige token para escritura.

    Mensajes de error posibles:
      - "Servidor sin API_SECRET_TOKEN configurado."
      - "Falta Authorization: Bearer <token> o X-API-KEY."
      - "Token inválido."
      - "Credenciales no válidas o ausentes." (valor por defecto)
    """

    message = "Credenciales no válidas o ausentes."

    # ------------------------------
    # Helpers internos
    # ------------------------------
    def _expected_token(self) -> Optional[str]:
        """Obtiene el token esperado desde el entorno (o None si no está)."""
        return env("API_SECRET_TOKEN", default=None)

    def _provided_token(self, request) -> Optional[str]:
        """
        Extrae el token de la petición HTTP:
          - Authorization: Bearer <token>
          - X-API-KEY: <token>
        """
        auth_header = request.headers.get("Authorization", "")
        if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()

        api_key = request.headers.get("X-API-KEY")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

        return None

    # ------------------------------
    # Hook de permisos DRF
    # ------------------------------
    def has_permission(self, request, view) -> bool:
        """
        Reglas:
          - Métodos seguros → True.
          - Escritura → requiere coincidencia entre token enviado y esperado.
        """
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

        self.message = "Token inválido."
        return False
