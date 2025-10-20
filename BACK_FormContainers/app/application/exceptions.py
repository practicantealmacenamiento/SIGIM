# -*- coding: utf-8 -*-
"""
Excepciones visibles desde la capa de aplicación.

Objetivo:
- Re-exportar las excepciones del dominio para que los casos de uso/servicios
  no dependan directamente del paquete `app.domain.exceptions`.
- No definir nuevas excepciones “de dominio” aquí.

Notas:
- Si en el futuro la aplicación necesita excepciones **propias** (p. ej. errores
  de orquestación, timeouts de infraestructura, etc.), deberían vivir en la
  capa de infraestructura o como “application errors” que no sean reutilizadas
  por el dominio.
"""

from __future__ import annotations

# Re-export explícito de excepciones del dominio
from app.domain.exceptions import (
    DomainException as DomainException,
    DomainError as DomainError,  # alias de compatibilidad
    ValidationError as ValidationError,
    EntityNotFoundError as EntityNotFoundError,
    BusinessRuleViolationError as BusinessRuleViolationError,
    InvalidOperationError as InvalidOperationError,
    InvariantViolationError as InvariantViolationError,
)

# API pública de este módulo (mapea 1:1 a lo re-exportado)
__all__ = [
    "DomainException",
    "DomainError",               # alias
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "InvariantViolationError",
]
