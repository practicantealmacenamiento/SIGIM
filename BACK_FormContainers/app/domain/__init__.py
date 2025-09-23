"""
Capa de dominio - Clean Architecture

Esta capa contiene:
- Entidades de negocio (entities.py)
- Reglas de negocio (rules.py) 
- Puertos/Interfaces (ports.py)
- Repositorios/Protocolos (repositories.py)
- Excepciones del dominio (exceptions.py)

La capa de dominio es independiente de frameworks externos y representa
la lógica de negocio pura del sistema.
"""

# Exportar excepciones del dominio para fácil acceso
from .exceptions import (
    DomainException,
    DomainError,
    ValidationError,
    EntityNotFoundError,
    BusinessRuleViolationError,
    InvalidOperationError,
    InvariantViolationError,
)

# Exportar entidades principales
from .entities import (
    Answer,
    Question,
    Choice,
    Questionnaire,
)

__all__ = [
    # Excepciones
    "DomainException",
    "DomainError", 
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError", 
    "InvalidOperationError",
    "InvariantViolationError",
    # Entidades
    "Answer",
    "Question", 
    "Choice",
    "Questionnaire",
]