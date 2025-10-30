"""Puertos del dominio hacia servicios externos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

__all__ = [
    "ExtractionMode",
    "ExtractionResult",
    "TextExtractorPort",
    "FileStorage",
]


# ---------------------------------------------------------------------------
# OCR / extracción de texto
# ---------------------------------------------------------------------------


class ExtractionMode(Enum):
    """Modos admitidos para la extracción de texto."""

    TEXT = "text"
    DOCUMENT = "document"
    HANDWRITING = "handwriting"


class ExtractionResult:
    """Encapsula el resultado de una operación de OCR."""

    def __init__(
        self,
        text: str,
        confidence: Optional[float] = None,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.text = text
        self.confidence = confidence
        self.bounding_boxes = bounding_boxes or []
        self.metadata = metadata or {}


class TextExtractorPort(ABC):
    """Contrato que debe cumplir un proveedor de OCR."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """Devuelve texto plano extraído de la imagen."""

    @abstractmethod
    def extract_text_with_mode(self, image_bytes: bytes, mode: ExtractionMode = ExtractionMode.TEXT) -> str:
        """Devuelve texto usando un modo específico del proveedor."""

    @abstractmethod
    def extract_text_detailed(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None,
    ) -> ExtractionResult:
        """Devuelve texto acompañado de confianza y bounding boxes."""

    @abstractmethod
    def extract_structured_text(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Devuelve texto estructurado para documentos complejos."""

    @abstractmethod
    def validate_image(self, image_bytes: bytes) -> bool:
        """Valida si la imagen es apta para OCR."""


# ---------------------------------------------------------------------------
# Almacenamiento de archivos
# ---------------------------------------------------------------------------


class FileStorage(Protocol):
    """Contrato mínimo que debe cumplir un backend de almacenamiento."""

    def save(self, *, folder: str, file_obj) -> str:
        """Guarda un archivo y devuelve la ruta relativa asignada."""

    def delete(self, *, path: str) -> None:
        """Elimina un archivo de forma idempotente."""
