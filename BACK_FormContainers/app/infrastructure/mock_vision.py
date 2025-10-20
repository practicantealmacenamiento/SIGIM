# -*- coding: utf-8 -*-
"""
Extractor de texto simulado (mock) para desarrollo y pruebas.

Este módulo provee una implementación ficticia de `TextExtractorPort` que puede
usarse durante el desarrollo o en tests cuando el proveedor real (p. ej. Google
Cloud Vision) no está disponible.

Características:
- Genera respuestas verosímiles basadas en patrones comunes de OCR.
- Permite validar reglas de negocio sin depender de servicios externos.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import re  # reservado por si se requieren patrones adicionales

from app.domain.ports import ExtractionMode, ExtractionResult, TextExtractorPort
from app.domain.exceptions import ExtractionError, InvalidImageError

__all__ = ["MockTextExtractor", "DevelopmentTextExtractor"]


class MockTextExtractor(TextExtractorPort):
    """
    Extractor de texto simulado para desarrollo.

    Este adaptador devuelve respuestas de ejemplo basadas en el tamaño de la
    imagen (en bytes) para emular comportamientos típicos de OCR.
    """

    def __init__(self, *, mode: str = "text", language_hints: Optional[List[str]] = None):
        self.mode = (mode or "text").lower()
        self.language_hints = list(language_hints or [])

    # ------------------------------------------------------------------ #
    #   API del puerto
    # ------------------------------------------------------------------ #

    def extract_text(self, image_bytes: bytes) -> str:
        """Extrae texto simulado a partir de bytes de imagen."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Formato de imagen inválido o datos vacíos.",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )

        # Generar texto simulado en función del tamaño para variar respuestas
        image_size = len(image_bytes)

        if image_size < 1000:
            return "ABC123"  # Imagen pequeña → texto simple (placa)
        elif image_size < 10000:
            return "PLACA ABC123 CONTENEDOR MSCU1234567"  # Imagen mediana
        else:
            return "DOCUMENTO TRANSPORTE\nPLACA: ABC123\nCONTENEDOR: MSCU1234567\nPRECINTO: TDM38816"

    def extract_text_with_mode(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
    ) -> str:
        """Extrae texto usando un modo específico (TEXT/DOCUMENT/HANDWRITING)."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Formato de imagen inválido o datos vacíos.",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )

        base_text = self.extract_text(image_bytes)

        if mode == ExtractionMode.DOCUMENT:
            # Modo documento: añade cabecera y fecha simulada
            return f"DOCUMENTO OFICIAL\n{base_text}\nFECHA: 2024-01-15"
        elif mode == ExtractionMode.HANDWRITING:
            # Manuscrito: simula menor precisión
            return base_text.replace("123", "1Z3").replace("ABC", "A8C")
        else:
            return base_text

    def extract_text_detailed(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None,
    ) -> ExtractionResult:
        """
        Extrae texto con información adicional: confianza, bounding boxes y metadatos.
        """
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Formato de imagen inválido o datos vacíos.",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )

        text = self.extract_text_with_mode(image_bytes, mode)

        # Generar bounding boxes simulados por palabra
        words = text.split()
        bounding_boxes = []
        x_offset = 10

        for word in words:
            bounding_boxes.append({
                "text": word,
                "vertices": [
                    {"x": x_offset, "y": 10},
                    {"x": x_offset + len(word) * 8, "y": 10},
                    {"x": x_offset + len(word) * 8, "y": 30},
                    {"x": x_offset, "y": 30},
                ],
            })
            x_offset += len(word) * 8 + 5

        return ExtractionResult(
            text=text,
            confidence=0.95,  # Confianza simulada alta
            bounding_boxes=bounding_boxes,
            metadata={
                "mode": mode.value,
                "language_hints": language_hints or self.language_hints,
                "mock": True,
            },
        )

    def extract_structured_text(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extrae texto estructurado para documentos complejos (mock).
        Retorna estructura con páginas/bloques/párrafos/palabras y confianza simulada.
        """
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Formato de imagen inválido o datos vacíos.",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )

        text = self.extract_text(image_bytes)
        words = text.split()

        return {
            "full_text": text,
            "pages": [{
                "blocks": [{
                    "paragraphs": [{
                        "words": [{"text": word, "confidence": 0.95} for word in words],
                        "confidence": 0.95,
                    }],
                    "confidence": 0.95,
                }],
            }],
            # Estructuras planas adicionales para facilitar tests
            "blocks": [{
                "paragraphs": [{
                    "words": [{"text": word, "confidence": 0.95} for word in words],
                    "confidence": 0.95,
                }],
                "confidence": 0.95,
            }],
            "paragraphs": [{
                "words": [{"text": word, "confidence": 0.95} for word in words],
                "confidence": 0.95,
            }],
            "words": words,
        }

    def validate_image(self, image_bytes: bytes) -> bool:
        """
        Valida si la imagen es procesable por el servicio OCR (mock).

        Comprobaciones:
        - No vacía.
        - Prefiere detectar firmas mágicas de formatos comunes (JPEG, PNG, GIF, WebP, BMP).
        - Para fines de mock, acepta cualquier buffer no vacío.
        """
        if not image_bytes or len(image_bytes) == 0:
            return False

        # Firmas mágicas de formatos típicos
        image_signatures = [
            b"\xff\xd8\xff",          # JPEG
            b"\x89PNG\r\n\x1a\n",     # PNG
            b"GIF87a",                # GIF87a
            b"GIF89a",                # GIF89a
            b"RIFF",                  # WebP (encabezado RIFF)
            b"BM",                    # BMP
        ]

        for signature in image_signatures:
            if image_bytes.startswith(signature):
                return True

        # En modo simulado aceptamos cualquier buffer no vacío
        return len(image_bytes) > 0


class DevelopmentTextExtractor(MockTextExtractor):
    """
    Extractor de texto para desarrollo con respuestas predefinidas.

    Útil para probar reglas de negocio/validaciones generando distintos
    patrones de salida a partir del tamaño del archivo.
    """

    def extract_text(self, image_bytes: bytes) -> str:
        """Extrae texto con patrones específicos para desarrollo."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Formato de imagen inválido o datos vacíos.",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )

        # Usar el tamaño como “hash” simple para seleccionar respuesta
        image_size = len(image_bytes)

        responses = [
            "ABC123",  # Placa válida
            "MSCU1234567",  # Contenedor válido
            "TDM38816",  # Precinto válido
            "PLACA ABC123 CONTENEDOR MSCU1234567",  # Múltiples elementos
            "DOCUMENTO TRANSPORTE\nPLACA: DEF456\nCONTENEDOR: TCLU9876543\nPRECINTO: XYZ12345",
            "INVALID TEXT NO PATTERNS",  # Sin patrones reconocibles
            "123456789",  # Solo números
            "ABCDEFGH",  # Solo letras
        ]

        return responses[image_size % len(responses)]
