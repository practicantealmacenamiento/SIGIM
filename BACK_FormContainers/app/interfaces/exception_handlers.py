"""
Traductor de excepciones de dominio a respuestas HTTP (capa de interfaces).

- No acopla dominio a DRF: sólo aquí conocemos Response/HTTP.
- Ofrece:
  * DomainExceptionTranslator: mapea DomainException -> Response
  * translate_domain_exception(): helper
  * handle_domain_exception_decorator: decorador para vistas puntuales
  * DomainExceptionMiddleware: captura DomainException a nivel middleware
  * custom_exception_handler: para integrarlo con DRF (REST_FRAMEWORK.EXCEPTION_HANDLER)
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Any, Type

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_exception_handler

# Importa únicamente tipos de dominio; NO modelos ni infra.
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
    Traductor centralizado de DomainException -> HTTP Response.

    Notas:
    - Sólo serializa información segura para el cliente.
    - Incluye un `error_id` (UUID) para correlación en logs.
    """

    # Mapeo de tipos de excepción a códigos de estado HTTP
    _STATUS_CODE_MAP: Dict[Type[DomainException], int] = {
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

    # Mapeo de tipos de excepción a tipos de error legibles por el cliente
    _ERROR_TYPE_MAP: Dict[Type[DomainException], str] = {
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
        Traduce una DomainException a Response DRF con payload consistente.
        """
        status_code = cls._get_status_code(exception)
        error_type = cls._get_error_type(exception)
        error_id = str(uuid.uuid4())

        response_data = cls._build_response_data(exception, error_type, error_id)
        cls._log_exception(exception, status_code, error_id)

        return Response(response_data, status=status_code)

    # ---------- Helpers internos ----------

    @classmethod
    def _get_status_code(cls, exception: DomainException) -> int:
        return cls._STATUS_CODE_MAP.get(type(exception), status.HTTP_500_INTERNAL_SERVER_ERROR)

    @classmethod
    def _get_error_type(cls, exception: DomainException) -> str:
        return cls._ERROR_TYPE_MAP.get(type(exception), "domain_error")

    @classmethod
    def _build_response_data(cls, exception: DomainException, error_type: str, error_id: str) -> Dict[str, Any]:
        """
        Payload estándar:
        {
          "error_id": "<uuid>",
          "type": "validation_error",
          "code": "SOME_CODE",        # si la excepción define .code
          "error": "Mensaje...",
          "details": {...}|[...]|"...",  # si define .details
          "extra": {...}              # si define .extra (no sensible)
        }
        """
        data: Dict[str, Any] = {
            "error_id": error_id,
            "type": error_type,
            "error": str(exception) if str(exception) else type(exception).__name__,
        }

        # Campos opcionales habituales en excepciones de dominio
        code = getattr(exception, "code", None)
        if code:
            data["code"] = code

        details = getattr(exception, "details", None)
        if details:
            data["details"] = details

        extra = getattr(exception, "extra", None)
        if extra and isinstance(extra, dict):
            data["extra"] = extra

        return data

    @classmethod
    def _log_exception(cls, exception: DomainException, status_code: int, error_id: str) -> None:
        """
        Log estructurado para correlación. Si usas Sentry/ELK, el error_id ayuda al soporte.
        """
        log_level = logging.WARNING if status_code < 500 else logging.ERROR
        logger.log(
            log_level,
            "Domain exception -> HTTP %s [%s]: %s: %s",
            status_code,
            error_id,
            type(exception).__name__,
            str(exception),
            extra={
                "status": status_code,
                "error_id": error_id,
                "ex_type": type(exception).__name__,
                "exception_details": getattr(exception, "details", None),
                "exception_code": getattr(exception, "code", None),
                "exception_message": str(exception),
            },
            exc_info=(status_code >= 500),  # adjunta traceback sólo en 5xx
        )


# ---------------------------
# API pública del módulo
# ---------------------------

def translate_domain_exception(exception: DomainException) -> Response:
    """Función de conveniencia: DomainException -> Response."""
    return DomainExceptionTranslator.translate(exception)


def handle_domain_exception_decorator(view_func):
    """
    Decorador para vistas/handlers que lanzen DomainException.
    Ejemplo:
        @handle_domain_exception_decorator
        def my_view(request):
            service.do()  # puede lanzar DomainException
            ...
    """
    def wrapper(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except DomainException as e:
            return translate_domain_exception(e)
    return wrapper


class DomainExceptionMiddleware:
    """
    Middleware para capturar DomainException en toda la app.

    settings.py:
        MIDDLEWARE = [
            ...,
            "app.interfaces.exception_handlers.DomainExceptionMiddleware",
        ]
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except DomainException as e:
            return translate_domain_exception(e)

    def process_exception(self, request, exception):
        """
        Compat con el hook de middlewares que implementan process_exception.
        """
        if isinstance(exception, DomainException):
            return translate_domain_exception(exception)
        return None


def custom_exception_handler(exc, context):
    """
    Handler para DRF: prioriza DomainException y delega al default para el resto.

    settings.py:
        REST_FRAMEWORK = {
            "EXCEPTION_HANDLER": "app.interfaces.exception_handlers.custom_exception_handler",
        }
    """
    if isinstance(exc, DomainException):
        return translate_domain_exception(exc)
    # Delega al handler por defecto de DRF (APIException, ValidationError de DRF, etc.)
    return drf_default_exception_handler(exc, context)


__all__ = [
    "DomainExceptionTranslator",
    "translate_domain_exception",
    "handle_domain_exception_decorator",
    "DomainExceptionMiddleware",
    "custom_exception_handler",
]
