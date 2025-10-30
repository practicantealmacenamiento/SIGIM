"""Excepciones específicas del dominio.

Cada excepción describe un escenario de negocio o de infraestructura interna
que debe poder propagarse sin depender de frameworks externos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

__all__ = [
    "DomainException",
    "DomainError",
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "InvariantViolationError",
    "ExtractionError",
    "InvalidImageError",
    "NotificationError",
    "InvalidRecipientError",
    "TemplateNotFoundError",
    "InvalidTemplateDataError",
    "InvalidScheduleTimeError",
    "NotificationNotFoundError",
    "FileStorageError",
    "InvalidFileError",
]


# ---------------------------------------------------------------------------
# Clase base
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class DomainException(Exception):
    """Excepción base para todo error del dominio."""

    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str: 
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


DomainError = DomainException  # alias histórico


# ---------------------------------------------------------------------------
# Validación y existencia
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class ValidationError(DomainException):
    """Datos inválidos para el dominio."""

    field: Optional[str] = None

    def __post_init__(self) -> None:
        if self.field and self.details is None:
            self.details = {"field": self.field}


@dataclass(eq=False)
class EntityNotFoundError(DomainException):
    """La entidad solicitada no existe."""

    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.entity_type and self.entity_id and self.details is None:
            self.details = {"entity_type": self.entity_type, "entity_id": self.entity_id}


# ---------------------------------------------------------------------------
# Reglas de negocio e invariantes
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class BusinessRuleViolationError(DomainException):
    """Se intentó ejecutar una acción prohibida por el dominio."""

    rule_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.rule_name and self.details is None:
            self.details = {"rule_name": self.rule_name}


@dataclass(eq=False)
class InvalidOperationError(DomainException):
    """Operación inválida para el estado actual de la entidad."""

    operation: Optional[str] = None

    def __post_init__(self) -> None:
        if self.operation and self.details is None:
            self.details = {"operation": self.operation}


@dataclass(eq=False)
class InvariantViolationError(DomainException):
    """Se violó una invariante del dominio."""

    invariant_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.invariant_name and self.details is None:
            self.details = {"invariant_name": self.invariant_name}


# ---------------------------------------------------------------------------
# Errores asociados a OCR / imágenes
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class ExtractionError(DomainException):
    """La extracción de texto fracasó en el servicio de OCR."""

    service_name: Optional[str] = None
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.service_name and self.details is None:
            self.details = {"service_name": self.service_name, "error_code": self.error_code}


@dataclass(eq=False)
class InvalidImageError(DomainException):
    """La imagen recibida no es válida para el proceso."""

    image_format: Optional[str] = None
    image_size: Optional[int] = None

    def __post_init__(self) -> None:
        if self.image_format and self.details is None:
            self.details = {"image_format": self.image_format, "image_size": self.image_size}


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class NotificationError(DomainException):
    """Fallo genérico durante el envío de una notificación."""

    provider: Optional[str] = None

    def __post_init__(self) -> None:
        if self.provider and self.details is None:
            self.details = {"provider": self.provider}


@dataclass(eq=False)
class InvalidRecipientError(DomainException):
    """El destinatario de la notificación es inválido."""

    recipient: Optional[str] = None

    def __post_init__(self) -> None:
        if self.recipient and self.details is None:
            self.details = {"recipient": self.recipient}


@dataclass(eq=False)
class TemplateNotFoundError(DomainException):
    """La plantilla de notificación solicitada no existe."""

    template_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.template_id and self.details is None:
            self.details = {"template_id": self.template_id}


@dataclass(eq=False)
class InvalidTemplateDataError(DomainException):
    """Los datos suministrados para la plantilla son incorrectos."""

    template_id: Optional[str] = None
    missing_fields: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.template_id and self.details is None:
            self.details = {
                "template_id": self.template_id,
                "missing_fields": self.missing_fields,
            }


@dataclass(eq=False)
class InvalidScheduleTimeError(DomainException):
    """El horario indicado para la notificación no es válido."""

    scheduled_time: Optional[str] = None

    def __post_init__(self) -> None:
        if self.scheduled_time and self.details is None:
            self.details = {"scheduled_time": self.scheduled_time}


@dataclass(eq=False)
class NotificationNotFoundError(DomainException):
    """La notificación buscada no existe."""

    notification_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.notification_id and self.details is None:
            self.details = {"notification_id": self.notification_id}


# ---------------------------------------------------------------------------
# Almacenamiento de archivos
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class FileStorageError(DomainException):
    """El servicio de almacenamiento falló durante la operación."""

    storage_type: Optional[str] = None
    operation: Optional[str] = None
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.storage_type and self.details is None:
            self.details = {
                "storage_type": self.storage_type,
                "operation": self.operation,
                "error_code": self.error_code,
            }


@dataclass(eq=False)
class InvalidFileError(DomainException):
    """El archivo proporcionado no cumple los requisitos del storage."""

    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None

    def __post_init__(self) -> None:
        if self.file_name and self.details is None:
            self.details = {
                "file_name": self.file_name,
                "file_size": self.file_size,
                "file_type": self.file_type,
            }
