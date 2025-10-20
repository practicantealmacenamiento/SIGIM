# -*- coding: utf-8 -*-
"""
Puertos (interfaces) de la capa de dominio hacia tecnologías externas.

Este módulo define contratos abstractos —sin dependencias de infraestructura—
para integrar servicios como:
- OCR / extracción de texto desde imágenes.
- Envío de notificaciones (email, SMS, push, in-app, webhooks).
- Almacenamiento de archivos (save/delete).

Notas:
- No hay lógica de negocio aquí; sólo contratos y tipos auxiliares.
- Las implementaciones viven en la capa de infraestructura y deben cumplir estos contratos.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

# ── API pública del módulo ─────────────────────────────────────────────────────
__all__ = [
    # OCR
    "ExtractionMode",
    "ExtractionResult",
    "TextExtractorPort",
    # Notificaciones
    "NotificationType",
    "NotificationPriority",
    "NotificationResult",
    "NotificationServicePort",
    # Storage
    "FileStorage",
]


# ==============================================================================
#   OCR / Extracción de texto
# ==============================================================================

class ExtractionMode(Enum):
    """Modos de extracción de texto disponibles."""
    TEXT = "text"           # Detección básica de texto.
    DOCUMENT = "document"   # Detección en documentos estructurados.
    HANDWRITING = "handwriting"  # Detección de texto manuscrito.


class ExtractionResult:
    """
    Resultado de una operación de extracción de texto.

    Attributes:
        text: Texto extraído consolidado.
        confidence: Confianza global (si el proveedor la expone).
        bounding_boxes: Lista de cuadros delimitadores por bloque/línea/palabra.
        metadata: Metadatos específicos del proveedor (idiomas, versión, tiempos, etc.).
    """

    def __init__(
        self,
        text: str,
        confidence: Optional[float] = None,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.bounding_boxes = bounding_boxes or []
        self.metadata = metadata or {}


class TextExtractorPort(ABC):
    """
    Puerto para servicios de extracción de texto desde imágenes.

    Define contratos para diferentes tipos de extracción OCR:
      - Extracción básica de texto.
      - Extracción por modo (document, handwriting).
      - Extracción detallada con confianza y bounding boxes.
      - Extracción estructurada para documentos complejos.
    """

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """
        Extrae texto básico desde bytes de imagen.

        Args:
            image_bytes: Bytes de la imagen a procesar.

        Returns:
            Texto extraído de la imagen.

        Raises:
            ExtractionError: Si la extracción falla.
            InvalidImageError: Si la imagen es inválida.
        """
        ...

    @abstractmethod
    def extract_text_with_mode(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
    ) -> str:
        """
        Extrae texto usando un modo específico de extracción.

        Args:
            image_bytes: Bytes de la imagen a procesar.
            mode: Modo de extracción a utilizar.

        Returns:
            Texto extraído de la imagen.

        Raises:
            ExtractionError: Si la extracción falla.
            InvalidImageError: Si la imagen es inválida.
        """
        ...

    @abstractmethod
    def extract_text_detailed(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None,
    ) -> ExtractionResult:
        """
        Extrae texto con información detallada (confianza y ubicación).

        Args:
            image_bytes: Bytes de la imagen a procesar.
            mode: Modo de extracción a utilizar.
            language_hints: Códigos de idioma (BCP-47) para mejorar precisión.

        Returns:
            ExtractionResult con texto, confianza, bounding boxes y metadatos.

        Raises:
            ExtractionError: Si la extracción falla.
            InvalidImageError: Si la imagen es inválida.
        """
        ...

    @abstractmethod
    def extract_structured_text(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extrae texto estructurado para documentos con layouts complejos.

        Útil para documentos con múltiples secciones, tablas o layouts complejos.

        Args:
            image_bytes: Bytes de la imagen a procesar.
            language_hints: Lista de códigos de idioma para mejorar la precisión.

        Returns:
            Estructura con texto organizado por bloques, párrafos, tablas, etc.

        Raises:
            ExtractionError: Si la extracción falla.
            InvalidImageError: Si la imagen es inválida.
        """
        ...

    @abstractmethod
    def validate_image(self, image_bytes: bytes) -> bool:
        """
        Valida si una imagen es procesable por el servicio OCR.

        Args:
            image_bytes: Bytes de la imagen a validar.

        Returns:
            True si la imagen es válida para procesamiento.
        """
        ...


# ==============================================================================
#   Notificaciones
# ==============================================================================

class NotificationType(Enum):
    """Tipos de notificación disponibles."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Niveles de prioridad para notificaciones."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationResult:
    """
    Resultado de una operación de notificación.

    Attributes:
        success: Indica si la operación fue exitosa.
        message_id: Identificador retornado por el proveedor (si aplica).
        error_message: Mensaje de error descriptivo (si falló).
        metadata: Metadatos del proveedor (códigos, tiempo, cuotas, etc.).
    """

    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.message_id = message_id
        self.error_message = error_message
        self.metadata = metadata or {}


class NotificationServicePort(ABC):
    """
    Puerto para servicios de notificación del sistema.

    Define contratos para envío de diferentes tipos de notificaciones:
      - Email
      - SMS
      - Push
      - In-app
      - Webhooks
    """

    @abstractmethod
    def send_notification(
        self,
        recipient: str,
        message: str,
        subject: Optional[str] = None,
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> NotificationResult:
        """
        Envía una notificación básica a un destinatario.

        Args:
            recipient: Destinatario (email, teléfono, user_id, URL de webhook, etc.).
            message: Contenido del mensaje.
            subject: Asunto (opcional; principalmente para email).
            notification_type: Tipo de notificación a enviar.
            priority: Prioridad de la notificación.

        Returns:
            NotificationResult con el resultado de envío.

        Raises:
            NotificationError: Si el envío falla.
            InvalidRecipientError: Si el destinatario es inválido.
        """
        ...

    @abstractmethod
    def send_bulk_notification(
        self,
        recipients: List[str],
        message: str,
        subject: Optional[str] = None,
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> List[NotificationResult]:
        """
        Envía una notificación a múltiples destinatarios.

        Args:
            recipients: Lista de destinatarios.
            message: Contenido del mensaje.
            subject: Asunto (opcional).
            notification_type: Tipo de notificación a enviar.
            priority: Prioridad de la notificación.

        Returns:
            Lista de NotificationResult, uno por destinatario.

        Raises:
            NotificationError: Si el envío masivo falla.
        """
        ...

    @abstractmethod
    def send_templated_notification(
        self,
        recipient: str,
        template_id: str,
        template_data: Dict[str, Any],
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> NotificationResult:
        """
        Envía una notificación usando una plantilla predefinida.

        Args:
            recipient: Destinatario de la notificación.
            template_id: ID de la plantilla a utilizar.
            template_data: Datos para rellenar la plantilla.
            notification_type: Tipo de notificación a enviar.
            priority: Prioridad de la notificación.

        Returns:
            NotificationResult con el resultado de envío.

        Raises:
            NotificationError: Si el envío falla.
            TemplateNotFoundError: Si la plantilla no existe.
            InvalidTemplateDataError: Si los datos de la plantilla son inválidos.
        """
        ...

    @abstractmethod
    def send_system_alert(
        self,
        alert_type: str,
        message: str,
        recipients: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[NotificationResult]:
        """
        Envía alertas del sistema a administradores o usuarios específicos.

        Args:
            alert_type: Tipo de alerta (error, warning, info, etc.).
            message: Mensaje de la alerta.
            recipients: Lista de destinatarios para la alerta.
            metadata: Metadatos adicionales de la alerta.

        Returns:
            Lista de NotificationResult.

        Raises:
            NotificationError: Si el envío de la alerta falla.
        """
        ...

    @abstractmethod
    def schedule_notification(
        self,
        recipient: str,
        message: str,
        scheduled_time: Any,  # datetime compatible
        subject: Optional[str] = None,
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> str:
        """
        Programa una notificación para ser enviada en un momento específico.

        Args:
            recipient: Destinatario de la notificación.
            message: Contenido del mensaje.
            scheduled_time: Momento en que debe enviarse (datetime).
            subject: Asunto (opcional).
            notification_type: Tipo de notificación a enviar.
            priority: Prioridad de la notificación.

        Returns:
            ID de la notificación programada.

        Raises:
            NotificationError: Si la programación falla.
            InvalidScheduleTimeError: Si el tiempo programado es inválido.
        """
        ...

    @abstractmethod
    def cancel_scheduled_notification(self, notification_id: str) -> bool:
        """
        Cancela una notificación programada.

        Args:
            notification_id: ID de la notificación a cancelar.

        Returns:
            True si la cancelación fue exitosa.

        Raises:
            NotificationNotFoundError: Si la notificación no existe.
        """
        ...

    @abstractmethod
    def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de una notificación enviada o programada.

        Args:
            notification_id: ID de la notificación.

        Returns:
            Estructura con estado (sent, pending, failed, etc.).
        """
        ...

    @abstractmethod
    def validate_recipient(
        self,
        recipient: str,
        notification_type: NotificationType,
    ) -> bool:
        """
        Valida si un destinatario es válido para el tipo de notificación.

        Args:
            recipient: Destinatario a validar.
            notification_type: Tipo de notificación.

        Returns:
            True si el destinatario es válido.
        """
        ...


# ==============================================================================
#   Storage de archivos
# ==============================================================================

class FileStorage(Protocol):
    """
    Puerto para almacenamiento de archivos.

    Contrato mínimo esperado por la capa de aplicación/servicios. Debe retornar
    la ruta relativa (name) persistida por el storage al guardar archivos.
    """

    def save(self, *, folder: str, file_obj) -> str:
        """
        Guarda un archivo en el `folder` indicado y devuelve su path relativo.

        Args:
            folder: Carpeta lógica o prefijo de almacenamiento.
            file_obj: Objeto archivo compatible con el backend (File, BytesIO, etc.).

        Returns:
            Ruta relativa (name) del recurso almacenado.
        """
        ...

    def delete(self, *, path: str) -> None:
        """
        Elimina un archivo del storage (idempotente).

        Args:
            path: Ruta relativa (name) del recurso a eliminar.
        """
        ...
