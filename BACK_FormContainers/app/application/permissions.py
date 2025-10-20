# -*- coding: utf-8 -*-
"""
Permisos de DRF para proteger métodos de escritura con un token de API.

Comportamiento:
- Métodos seguros (GET/HEAD/OPTIONS): permitidos sin autenticación.
- Métodos de escritura (POST/PUT/PATCH/DELETE): requieren un token válido.
- Orígenes válidos del token en la petición:
    * Cabecera `Authorization: Bearer <token>`
    * Cabecera `X-API-KEY: <token>`

El token esperado se obtiene de la variable de entorno `API_SECRET_TOKEN`.
Si no está configurada, se deniega el acceso a métodos de escritura de forma explícita.

Notas:
- Se usa `hmac.compare_digest` para comparación en tiempo constante.
- Este módulo lee `.env` al importar, replicando el comportamiento existente.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
import hmac
import os
from typing import Optional

# ── Terceros ───────────────────────────────────────────────────────────────────
import environ
from rest_framework.permissions import SAFE_METHODS, BasePermission

# ── Carga de entorno ───────────────────────────────────────────────────────────
env = environ.Env()
env.read_env(env_file=os.environ.get("ENV_FILE", ".env"))

__all__ = ["TokenRequiredForWrite"]


class TokenRequiredForWrite(BasePermission):
    """
    Permite métodos seguros sin restricción y exige token para escritura.

    Mensajes de error expuestos:
      - "Servidor sin API_SECRET_TOKEN configurado."
      - "Falta Authorization: Bearer <token> o X-API-KEY."
      - "Token inválido."
      - "Credenciales no válidas o ausentes." (por defecto)
    """

    message = "Credenciales no válidas o ausentes."

    # ------------------------------
    # Helpers internos (no públicos)
    # ------------------------------
    def _expected_token(self) -> Optional[str]:
        """
        Obtiene el token esperado desde el entorno.
        Devuelve None si no está configurado (no revienta).
        """
        return env("API_SECRET_TOKEN", default=None)

    def _provided_token(self, request) -> Optional[str]:
        """
        Extrae el token de la petición HTTP:
          - Authorization: Bearer <token>
          - X-API-KEY: <token>
        """
        # Authorization: Bearer <token>
        auth_header = request.headers.get("Authorization", "")
        if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()

        # Fallback: X-API-KEY: <token>
        api_key = request.headers.get("X-API-KEY")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

        return None

    # ------------------------------
    # DRF permission hook
    # ------------------------------
    def has_permission(self, request, view) -> bool:
        """
        Reglas:
          - Métodos seguros → True.
          - Escritura → requiere coincidencia `provided` vs `expected`.
        """
        # GET/HEAD/OPTIONS libres
        if request.method in SAFE_METHODS:
            return True

        expected = self._expected_token()
        provided = self._provided_token(request)

        if not expected:
            # Negar explícitamente si el servidor no está configurado
            self.message = "Servidor sin API_SECRET_TOKEN configurado."
            return False

        if not provided:
            self.message = "Falta Authorization: Bearer <token> o X-API-KEY."
            return False

        if hmac.compare_digest(provided, expected):
            return True

        self.message = "Token inválido."
        return False
