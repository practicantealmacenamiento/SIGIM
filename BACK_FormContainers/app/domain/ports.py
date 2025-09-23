from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol, Optional, List, Dict, Any
from enum import Enum


class ExtractionMode(Enum):
    """Modos de extracción de texto disponibles."""
    TEXT = "text"  # Detección básica de texto
    DOCUMENT = "document"  # Detección de texto en documentos estructurados
    HANDWRITING = "handwriting"  # Detección de texto manuscrito


class ExtractionResult:
    """Resultado de una operación de extracción de texto."""
    
    def __init__(
        self, 
        text: str, 
        confidence: Optional[float] = None,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.text = text
        self.confidence = confidence
        self.bounding_boxes = bounding_boxes or []
        self.metadata = metadata or {}


# ---- Puerto tecnológico: OCR/Text Extraction ----
class TextExtractorPort(ABC):
    """
    Puerto para servicios de extracción de texto desde imágenes.
    
    Define contratos para diferentes tipos de extracción OCR:
    - Extracción básica de texto
    - Extracción de documentos estructurados
    - Extracción con configuración específica
    - Extracción con información de confianza y ubicación
    """

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """
        Extrae texto básico desde bytes de imagen.
        
        Args:
            image_bytes: Bytes de la imagen a procesar
            
        Returns:
            str: Texto extraído de la imagen
            
        Raises:
            ExtractionError: Si la extracción falla
            InvalidImageError: Si la imagen es inválida
        """
        ...

    @abstractmethod
    def extract_text_with_mode(
        self, 
        image_bytes: bytes, 
        mode: ExtractionMode = ExtractionMode.TEXT
    ) -> str:
        """
        Extrae texto usando un modo específico de extracción.
        
        Args:
            image_bytes: Bytes de la imagen a procesar
            mode: Modo de extracción a utilizar
            
        Returns:
            str: Texto extraído de la imagen
            
        Raises:
            ExtractionError: Si la extracción falla
            InvalidImageError: Si la imagen es inválida
        """
        ...

    @abstractmethod
    def extract_text_detailed(
        self, 
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extrae texto con información detallada incluyendo confianza y ubicación.
        
        Args:
            image_bytes: Bytes de la imagen a procesar
            mode: Modo de extracción a utilizar
            language_hints: Lista de códigos de idioma para mejorar la precisión
            
        Returns:
            ExtractionResult: Resultado detallado con texto, confianza y metadatos
            
        Raises:
            ExtractionError: Si la extracción falla
            InvalidImageError: Si la imagen es inválida
        """
        ...

    @abstractmethod
    def extract_structured_text(
        self, 
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extrae texto estructurado para documentos complejos.
        
        Útil para documentos con múltiples secciones, tablas o layouts complejos.
        
        Args:
            image_bytes: Bytes de la imagen a procesar
            language_hints: Lista de códigos de idioma para mejorar la precisión
            
        Returns:
            Dict: Estructura con texto organizado por bloques, párrafos, etc.
            
        Raises:
            ExtractionError: Si la extracción falla
            InvalidImageError: Si la imagen es inválida
        """
        ...

    @abstractmethod
    def validate_image(self, image_bytes: bytes) -> bool:
        """
        Valida si una imagen es procesable por el servicio OCR.
        
        Args:
            image_bytes: Bytes de la imagen a validar
            
        Returns:
            bool: True si la imagen es válida para procesamiento
        """
        ...


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
    """Resultado de una operación de notificación."""
    
    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.message_id = message_id
        self.error_message = error_message
        self.metadata = metadata or {}


# ---- Puerto tecnológico: Notification Service ----
class NotificationServicePort(ABC):
    """
    Puerto para servicios de notificación del sistema.
    
    Define contratos para envío de diferentes tipos de notificaciones:
    - Notificaciones por email
    - Notificaciones SMS
    - Notificaciones push
    - Notificaciones in-app
    - Webhooks para sistemas externos
    """

    @abstractmethod
    def send_notification(
        self,
        recipient: str,
        message: str,
        subject: Optional[str] = None,
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> NotificationResult:
        """
        Envía una notificación básica a un destinatario.
        
        Args:
            recipient: Destinatario de la notificación (email, teléfono, user_id, etc.)
            message: Contenido del mensaje
            subject: Asunto de la notificación (opcional, usado principalmente en emails)
            notification_type: Tipo de notificación a enviar
            priority: Prioridad de la notificación
            
        Returns:
            NotificationResult: Resultado de la operación de envío
            
        Raises:
            NotificationError: Si el envío falla
            InvalidRecipientError: Si el destinatario es inválido
        """
        ...

    @abstractmethod
    def send_bulk_notification(
        self,
        recipients: List[str],
        message: str,
        subject: Optional[str] = None,
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> List[NotificationResult]:
        """
        Envía una notificación a múltiples destinatarios.
        
        Args:
            recipients: Lista de destinatarios
            message: Contenido del mensaje
            subject: Asunto de la notificación (opcional)
            notification_type: Tipo de notificación a enviar
            priority: Prioridad de la notificación
            
        Returns:
            List[NotificationResult]: Lista de resultados para cada destinatario
            
        Raises:
            NotificationError: Si el envío masivo falla
        """
        ...

    @abstractmethod
    def send_templated_notification(
        self,
        recipient: str,
        template_id: str,
        template_data: Dict[str, Any],
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> NotificationResult:
        """
        Envía una notificación usando una plantilla predefinida.
        
        Args:
            recipient: Destinatario de la notificación
            template_id: ID de la plantilla a utilizar
            template_data: Datos para rellenar la plantilla
            notification_type: Tipo de notificación a enviar
            priority: Prioridad de la notificación
            
        Returns:
            NotificationResult: Resultado de la operación de envío
            
        Raises:
            NotificationError: Si el envío falla
            TemplateNotFoundError: Si la plantilla no existe
            InvalidTemplateDataError: Si los datos de la plantilla son inválidos
        """
        ...

    @abstractmethod
    def send_system_alert(
        self,
        alert_type: str,
        message: str,
        recipients: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """
        Envía alertas del sistema a administradores o usuarios específicos.
        
        Args:
            alert_type: Tipo de alerta (error, warning, info, etc.)
            message: Mensaje de la alerta
            recipients: Lista de destinatarios para la alerta
            metadata: Metadatos adicionales de la alerta
            
        Returns:
            List[NotificationResult]: Lista de resultados para cada destinatario
            
        Raises:
            NotificationError: Si el envío de la alerta falla
        """
        ...

    @abstractmethod
    def schedule_notification(
        self,
        recipient: str,
        message: str,
        scheduled_time: Any,  # datetime object
        subject: Optional[str] = None,
        notification_type: NotificationType = NotificationType.EMAIL,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> str:
        """
        Programa una notificación para ser enviada en un momento específico.
        
        Args:
            recipient: Destinatario de la notificación
            message: Contenido del mensaje
            scheduled_time: Momento en que debe enviarse la notificación
            subject: Asunto de la notificación (opcional)
            notification_type: Tipo de notificación a enviar
            priority: Prioridad de la notificación
            
        Returns:
            str: ID de la notificación programada
            
        Raises:
            NotificationError: Si la programación falla
            InvalidScheduleTimeError: Si el tiempo programado es inválido
        """
        ...

    @abstractmethod
    def cancel_scheduled_notification(self, notification_id: str) -> bool:
        """
        Cancela una notificación programada.
        
        Args:
            notification_id: ID de la notificación a cancelar
            
        Returns:
            bool: True si la cancelación fue exitosa
            
        Raises:
            NotificationNotFoundError: Si la notificación no existe
        """
        ...

    @abstractmethod
    def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de una notificación enviada o programada.
        
        Args:
            notification_id: ID de la notificación
            
        Returns:
            Dict: Estado de la notificación (sent, pending, failed, etc.)
            
        Raises:
            NotificationNotFoundError: Si la notificación no existe
        """
        ...

    @abstractmethod
    def validate_recipient(
        self, 
        recipient: str, 
        notification_type: NotificationType
    ) -> bool:
        """
        Valida si un destinatario es válido para el tipo de notificación.
        
        Args:
            recipient: Destinatario a validar
            notification_type: Tipo de notificación
            
        Returns:
            bool: True si el destinatario es válido
        """
        ...


# ---- Puerto tecnológico: File Storage ----
class FileStorage(Protocol):
    """
    Puerto para almacenamiento de archivos.
    Retorna la ruta relativa (name) persistida por el storage.
    """

    def save(self, *, folder: str, file_obj) -> str:
        """Guarda un archivo y devuelve su 'path' relativo en el storage."""
        ...

    def delete(self, *, path: str) -> None:
        """Elimina un archivo del storage (idempotente)."""
        ...
