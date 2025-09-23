"""
Excepciones específicas de la capa de dominio.

Estas excepciones representan violaciones de reglas de negocio, validaciones de entidades
y errores conceptuales del dominio. Son independientes de cualquier framework o tecnología externa.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass(eq=False)
class DomainException(Exception):
    """
    Excepción base para todos los errores del dominio.
    
    Representa cualquier violación de reglas de negocio o invariantes del dominio.
    Todas las excepciones específicas del dominio deben heredar de esta clase.
    """
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', details={self.details})"


@dataclass(eq=False)
class ValidationError(DomainException):
    """
    Error de validación de entidades o reglas de negocio.
    
    Se lanza cuando una entidad no cumple con sus invariantes o cuando
    los datos de entrada no satisfacen las reglas de validación del dominio.
    
    Ejemplos:
    - Una respuesta (Answer) que no tiene texto, opción ni archivo
    - Un contenedor que no cumple con el formato ISO 6346
    - Una placa que no tiene el formato colombiano válido
    """
    field: Optional[str] = None

    def __post_init__(self):
        if self.field and self.details is None:
            self.details = {"field": self.field}


@dataclass(eq=False)
class EntityNotFoundError(DomainException):
    """
    Error cuando una entidad requerida no existe en el dominio.
    
    Se lanza cuando se intenta acceder a una entidad que debería existir
    pero no se encuentra en el repositorio correspondiente.
    
    Ejemplos:
    - Buscar una pregunta por ID que no existe
    - Intentar obtener un cuestionario que fue eliminado
    - Referenciar una opción de respuesta inexistente
    """
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    def __post_init__(self):
        if self.entity_type and self.entity_id and self.details is None:
            self.details = {
                "entity_type": self.entity_type,
                "entity_id": self.entity_id
            }


@dataclass(eq=False)
class BusinessRuleViolationError(DomainException):
    """
    Error por violación de reglas de negocio específicas.
    
    Se lanza cuando se intenta realizar una operación que viola
    las reglas de negocio establecidas en el dominio.
    
    Ejemplos:
    - Intentar finalizar un submission que ya está finalizado
    - Guardar una respuesta para una pregunta que no pertenece al cuestionario
    - Intentar avanzar a una pregunta cuando faltan respuestas obligatorias
    """
    rule_name: Optional[str] = None

    def __post_init__(self):
        if self.rule_name and self.details is None:
            self.details = {"rule_name": self.rule_name}


@dataclass(eq=False)
class InvalidOperationError(DomainException):
    """
    Error por operación inválida en el contexto actual.
    
    Se lanza cuando se intenta realizar una operación que no es válida
    dado el estado actual de las entidades del dominio.
    
    Ejemplos:
    - Intentar modificar una entidad inmutable después de su creación
    - Realizar operaciones en un submission que está en estado incorrecto
    - Intentar operaciones que requieren permisos específicos
    """
    operation: Optional[str] = None
    current_state: Optional[str] = None

    def __post_init__(self):
        if self.operation and self.details is None:
            self.details = {
                "operation": self.operation,
                "current_state": self.current_state
            }


@dataclass(eq=False)
class InvariantViolationError(DomainException):
    """
    Error por violación de invariantes de entidad.
    
    Se lanza cuando una entidad no puede mantener sus invariantes
    después de una operación o durante su construcción.
    
    Ejemplos:
    - Una entidad Answer sin ningún tipo de respuesta
    - Un Questionnaire sin preguntas
    - Datos inconsistentes entre campos relacionados
    """
    invariant_name: Optional[str] = None

    def __post_init__(self):
        if self.invariant_name and self.details is None:
            self.details = {"invariant_name": self.invariant_name}


@dataclass(eq=False)
class ExtractionError(DomainException):
    """
    Error durante la extracción de texto desde imágenes.
    
    Se lanza cuando el servicio de OCR falla por problemas técnicos
    como errores de red, credenciales inválidas, o problemas del servicio externo.
    
    Ejemplos:
    - Falla de conexión al servicio de Google Vision
    - Credenciales de API inválidas o expiradas
    - Límites de cuota excedidos en el servicio OCR
    """
    service_name: Optional[str] = None
    error_code: Optional[str] = None

    def __post_init__(self):
        if self.service_name and self.details is None:
            self.details = {
                "service_name": self.service_name,
                "error_code": self.error_code
            }


@dataclass(eq=False)
class InvalidImageError(DomainException):
    """
    Error por imagen inválida para procesamiento OCR.
    
    Se lanza cuando la imagen proporcionada no puede ser procesada
    por el servicio de extracción de texto.
    
    Ejemplos:
    - Imagen vacía o corrupta
    - Formato de imagen no soportado
    - Imagen demasiado pequeña o de baja calidad
    - Archivo que no es una imagen válida
    """
    image_format: Optional[str] = None
    image_size: Optional[int] = None

    def __post_init__(self):
        if self.image_format and self.details is None:
            self.details = {
                "image_format": self.image_format,
                "image_size": self.image_size
            }


@dataclass(eq=False)
class NotificationError(DomainException):
    """
    Error durante el envío de notificaciones.
    
    Se lanza cuando el servicio de notificaciones falla por problemas técnicos
    como errores de red, configuración inválida, o problemas del servicio externo.
    
    Ejemplos:
    - Falla de conexión al servicio de email
    - Configuración de SMTP inválida
    - Límites de cuota excedidos en el servicio de notificaciones
    - Error en el servicio de SMS o push notifications
    """
    service_name: Optional[str] = None
    notification_type: Optional[str] = None
    error_code: Optional[str] = None

    def __post_init__(self):
        if self.service_name and self.details is None:
            self.details = {
                "service_name": self.service_name,
                "notification_type": self.notification_type,
                "error_code": self.error_code
            }


@dataclass(eq=False)
class InvalidRecipientError(DomainException):
    """
    Error por destinatario inválido para notificaciones.
    
    Se lanza cuando el destinatario proporcionado no es válido
    para el tipo de notificación especificado.
    
    Ejemplos:
    - Email con formato inválido
    - Número de teléfono con formato incorrecto
    - User ID que no existe en el sistema
    - Webhook URL malformada
    """
    recipient: Optional[str] = None
    notification_type: Optional[str] = None

    def __post_init__(self):
        if self.recipient and self.details is None:
            self.details = {
                "recipient": self.recipient,
                "notification_type": self.notification_type
            }


@dataclass(eq=False)
class TemplateNotFoundError(DomainException):
    """
    Error cuando una plantilla de notificación no existe.
    
    Se lanza cuando se intenta usar una plantilla que no está
    registrada en el sistema de notificaciones.
    
    Ejemplos:
    - Template ID que no existe
    - Plantilla eliminada o desactivada
    - Template ID con formato incorrecto
    """
    template_id: Optional[str] = None

    def __post_init__(self):
        if self.template_id and self.details is None:
            self.details = {"template_id": self.template_id}


@dataclass(eq=False)
class InvalidTemplateDataError(DomainException):
    """
    Error por datos inválidos para plantilla de notificación.
    
    Se lanza cuando los datos proporcionados para rellenar una plantilla
    no son válidos o están incompletos.
    
    Ejemplos:
    - Faltan variables requeridas por la plantilla
    - Tipos de datos incorrectos para variables de plantilla
    - Datos que no pasan validación de la plantilla
    """
    template_id: Optional[str] = None
    missing_fields: Optional[List[str]] = None

    def __post_init__(self):
        if self.template_id and self.details is None:
            self.details = {
                "template_id": self.template_id,
                "missing_fields": self.missing_fields
            }


@dataclass(eq=False)
class InvalidScheduleTimeError(DomainException):
    """
    Error por tiempo de programación inválido para notificaciones.
    
    Se lanza cuando el tiempo especificado para programar una notificación
    no es válido.
    
    Ejemplos:
    - Fecha en el pasado
    - Formato de fecha/hora incorrecto
    - Fecha demasiado lejana en el futuro
    """
    scheduled_time: Optional[str] = None

    def __post_init__(self):
        if self.scheduled_time and self.details is None:
            self.details = {"scheduled_time": self.scheduled_time}


@dataclass(eq=False)
class NotificationNotFoundError(DomainException):
    """
    Error cuando una notificación específica no se encuentra.
    
    Se lanza cuando se intenta acceder a una notificación que no existe
    en el sistema.
    
    Ejemplos:
    - Notification ID que no existe
    - Notificación eliminada o expirada
    - ID con formato incorrecto
    """
    notification_id: Optional[str] = None

    def __post_init__(self):
        if self.notification_id and self.details is None:
            self.details = {"notification_id": self.notification_id}


@dataclass(eq=False)
class FileStorageError(DomainException):
    """
    Error durante operaciones de almacenamiento de archivos.
    
    Se lanza cuando el servicio de almacenamiento falla por problemas técnicos
    como errores de red, permisos insuficientes, o problemas del servicio de storage.
    
    Ejemplos:
    - Falla de conexión al servicio de almacenamiento
    - Permisos insuficientes para escribir archivos
    - Límites de cuota excedidos en el servicio de storage
    - Error en el sistema de archivos local
    """
    storage_type: Optional[str] = None
    operation: Optional[str] = None
    error_code: Optional[str] = None

    def __post_init__(self):
        if self.storage_type and self.details is None:
            self.details = {
                "storage_type": self.storage_type,
                "operation": self.operation,
                "error_code": self.error_code
            }


@dataclass(eq=False)
class InvalidFileError(DomainException):
    """
    Error por archivo inválido para almacenamiento.
    
    Se lanza cuando el archivo proporcionado no puede ser procesado
    o almacenado por el servicio de storage.
    
    Ejemplos:
    - Archivo vacío o corrupto
    - Formato de archivo no soportado
    - Archivo demasiado grande
    - Nombre de archivo inválido
    - Archivo sin extensión cuando es requerida
    """
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None

    def __post_init__(self):
        if self.file_name and self.details is None:
            self.details = {
                "file_name": self.file_name,
                "file_size": self.file_size,
                "file_type": self.file_type
            }


# Aliases para compatibilidad y conveniencia
DomainError = DomainException  # Alias para mantener compatibilidad


__all__ = [
    "DomainException",
    "DomainError",  # Alias
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