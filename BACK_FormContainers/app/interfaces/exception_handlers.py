"""
Traductor de excepciones de dominio a respuestas HTTP.

Este módulo maneja la traducción de excepciones específicas del dominio
a respuestas HTTP apropiadas, manteniendo la separación entre capas.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from rest_framework import status
from rest_framework.response import Response

from app.domain.exceptions import (
    DomainException,
    ValidationError,
    EntityNotFoundError,
    BusinessRuleViolationError,
    InvalidOperationError,
    InvariantViolationError,
    ExtractionError,
    InvalidImageError,
    NotificationError,
    InvalidRecipientError,
    TemplateNotFoundError,
    InvalidTemplateDataError,
    InvalidScheduleTimeError,
    NotificationNotFoundError,
)

logger = logging.getLogger(__name__)


class DomainExceptionTranslator:
    """
    Traductor centralizado de excepciones de dominio a respuestas HTTP.
    
    Mapea excepciones específicas del dominio a códigos de estado HTTP apropiados
    y formatos de respuesta consistentes.
    """

    # Mapeo de tipos de excepción a códigos de estado HTTP
    _STATUS_CODE_MAP = {
        ValidationError: status.HTTP_400_BAD_REQUEST,
        EntityNotFoundError: status.HTTP_404_NOT_FOUND,
        BusinessRuleViolationError: status.HTTP_400_BAD_REQUEST,
        InvalidOperationError: status.HTTP_400_BAD_REQUEST,
        InvariantViolationError: status.HTTP_400_BAD_REQUEST,
        ExtractionError: status.HTTP_502_BAD_GATEWAY,
        InvalidImageError: status.HTTP_400_BAD_REQUEST,
        NotificationError: status.HTTP_502_BAD_GATEWAY,
        InvalidRecipientError: status.HTTP_400_BAD_REQUEST,
        TemplateNotFoundError: status.HTTP_404_NOT_FOUND,
        InvalidTemplateDataError: status.HTTP_400_BAD_REQUEST,
        InvalidScheduleTimeError: status.HTTP_400_BAD_REQUEST,
        NotificationNotFoundError: status.HTTP_404_NOT_FOUND,
    }

    # Mapeo de tipos de excepción a tipos de error para el cliente
    _ERROR_TYPE_MAP = {
        ValidationError: "validation_error",
        EntityNotFoundError: "not_found_error",
        BusinessRuleViolationError: "business_rule_error",
        InvalidOperationError: "invalid_operation_error",
        InvariantViolationError: "invariant_violation_error",
        ExtractionError: "extraction_error",
        InvalidImageError: "invalid_image_error",
        NotificationError: "notification_error",
        InvalidRecipientError: "invalid_recipient_error",
        TemplateNotFoundError: "template_not_found_error",
        InvalidTemplateDataError: "invalid_template_data_error",
        InvalidScheduleTimeError: "invalid_schedule_time_error",
        NotificationNotFoundError: "notification_not_found_error",
    }

    @classmethod
    def translate(cls, exception: DomainException) -> Response:
        """
        Traduce una excepción de dominio a una respuesta HTTP apropiada.
        
        Args:
            exception: La excepción de dominio a traducir
            
        Returns:
            Response: Respuesta HTTP con código de estado y formato apropiados
        """
        # Obtener código de estado HTTP
        status_code = cls._get_status_code(exception)
        
        # Obtener tipo de error para el cliente
        error_type = cls._get_error_type(exception)
        
        # Construir respuesta
        response_data = cls._build_response_data(exception, error_type)
        
        # Log del error para debugging
        cls._log_exception(exception, status_code)
        
        return Response(response_data, status=status_code)

    @classmethod
    def _get_status_code(cls, exception: DomainException) -> int:
        """Obtiene el código de estado HTTP apropiado para la excepción."""
        exception_type = type(exception)
        return cls._STATUS_CODE_MAP.get(exception_type, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @classmethod
    def _get_error_type(cls, exception: DomainException) -> str:
        """Obtiene el tipo de error para el cliente."""
        exception_type = type(exception)
        return cls._ERROR_TYPE_MAP.get(exception_type, "domain_error")

    @classmethod
    def _build_response_data(cls, exception: DomainException, error_type: str) -> Dict[str, Any]:
        """
        Construye los datos de respuesta para la excepción.
        
        Args:
            exception: La excepción de dominio
            error_type: El tipo de error para el cliente
            
        Returns:
            Dict con los datos de respuesta
        """
        response_data = {
            "error": str(exception),
            "type": error_type,
        }
        
        # Incluir detalles adicionales si están disponibles
        if hasattr(exception, 'details') and exception.details:
            response_data["details"] = exception.details
            
        return response_data

    @classmethod
    def _log_exception(cls, exception: DomainException, status_code: int) -> None:
        """Log de la excepción para debugging y monitoreo."""
        log_level = logging.WARNING if status_code < 500 else logging.ERROR
        
        logger.log(
            log_level,
            f"Domain exception translated to HTTP {status_code}: {type(exception).__name__}: {exception}",
            extra={
                "exception_type": type(exception).__name__,
                "status_code": status_code,
                "exception_details": getattr(exception, 'details', None),
            }
        )


def translate_domain_exception(exception: DomainException) -> Response:
    """
    Función de conveniencia para traducir excepciones de dominio.
    
    Args:
        exception: La excepción de dominio a traducir
        
    Returns:
        Response: Respuesta HTTP apropiada
    """
    return DomainExceptionTranslator.translate(exception)


def handle_domain_exception_decorator(view_func):
    """
    Decorator para manejar automáticamente excepciones de dominio en vistas.
    
    Usage:
        @handle_domain_exception_decorator
        def my_view(request):
            # código que puede lanzar excepciones de dominio
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except DomainException as e:
            return translate_domain_exception(e)
    
    return wrapper


class DomainExceptionMiddleware:
    """
    Middleware para capturar y traducir excepciones de dominio automáticamente.
    
    Este middleware captura excepciones de dominio no manejadas y las traduce
    a respuestas HTTP apropiadas de forma automática.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except DomainException as e:
            return translate_domain_exception(e)

    def process_exception(self, request, exception):
        """
        Procesa excepciones no capturadas durante el procesamiento de la vista.
        
        Args:
            request: La request HTTP
            exception: La excepción lanzada
            
        Returns:
            Response si es una excepción de dominio, None en caso contrario
        """
        if isinstance(exception, DomainException):
            return translate_domain_exception(exception)
        return None


__all__ = [
    "DomainExceptionTranslator",
    "translate_domain_exception", 
    "handle_domain_exception_decorator",
    "DomainExceptionMiddleware",
]