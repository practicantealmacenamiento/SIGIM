"""
Excepciones de la capa de aplicación.

Esta capa puede re-exportar excepciones del dominio para conveniencia,
pero no debe definir excepciones que sean usadas por el dominio.
"""

# Re-exportar excepciones del dominio para conveniencia de la capa de aplicación
from app.domain.exceptions import (
    DomainException,
    DomainError,  # Alias
    ValidationError,
    EntityNotFoundError,
    BusinessRuleViolationError,
    InvalidOperationError,
    InvariantViolationError,
)

# Mantener compatibilidad con el código existente
DomainError = DomainException

__all__ = [
    "DomainException",
    "DomainError",
    "ValidationError", 
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "InvariantViolationError",
]