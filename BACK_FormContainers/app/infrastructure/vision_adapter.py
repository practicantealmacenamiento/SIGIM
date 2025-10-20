# -*- coding: utf-8 -*-
"""
app/infrastructure/vision_adapter.py
------------------------------------

Adaptador de OCR con *fallback* elegante.

Objetivo:
- Exponer una única implementación que cumpla el puerto `TextExtractorPort`.
- Intentar usar Google Cloud Vision si está disponible.
- Si no está disponible (o se fuerza), caer al extractor *mock* de desarrollo.

Control por entorno:
- `USE_MOCK_OCR=1`  -> fuerza modo mock (útil en dev/CI).
- `GCV_DISABLED=1`  -> trata Google Vision como no disponible.
- `GOOGLE_APPLICATION_CREDENTIALS=/ruta/key.json` (si tu adapter GCV lo usa).

Dependencias opcionales:
- Si `app.infrastructure.vision.GoogleVisionAdapter` no existe o falla,
  usamos `DevelopmentTextExtractor` del módulo `mock_vision`.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any

from app.domain.ports import TextExtractorPort, ExtractionMode, ExtractionResult
from app.domain.exceptions import InvalidImageError, ExtractionError

# -----------------------------------------------------------------------------
# Detección de disponibilidad de Google Vision (opcional)
# -----------------------------------------------------------------------------
GOOGLE_VISION_AVAILABLE = False
if os.getenv("GCV_DISABLED", "0") not in ("1", "true", "True"):
    try:
        # Importa el adaptador real de GCV si existe en tu proyecto
        from app.infrastructure.vision import GoogleVisionAdapter  # type: ignore
        GOOGLE_VISION_AVAILABLE = True
    except Exception:
        GOOGLE_VISION_AVAILABLE = False

# Mock siempre disponible para *fallback*
from app.infrastructure.mock_vision import DevelopmentTextExtractor


# =============================================================================
# Adaptador principal
# =============================================================================
class TextExtractorAdapter(TextExtractorPort):
    """
    Implementa `TextExtractorPort` con prioridad a Google Vision y *fallback* a mock.

    Uso típico:
        extractor = TextExtractorAdapter(mode="text", language_hints=["es","en"])
        text = extractor.extract_text(image_bytes)

    Notas:
    - Si `USE_MOCK_OCR=1`, siempre se usará el mock.
    - Si GCV no puede inicializarse, se loguea y se usa mock automáticamente.
    """

    def __init__(
        self,
        *,
        mode: str = "text",
        language_hints: Optional[List[str]] = None,
        credentials_path: Optional[str] = None,
    ):
        self.mode = (mode or "text").lower()
        self.language_hints = list(language_hints or [])
        self._is_mock = True  # por defecto asumimos mock

        force_mock = os.getenv("USE_MOCK_OCR", "0") in ("1", "true", "True")

        if not force_mock and GOOGLE_VISION_AVAILABLE:
            try:
                # Pasa credenciales si tu adapter real lo acepta
                self._extractor = GoogleVisionAdapter(
                    mode=self.mode,
                    language_hints=self.language_hints,
                    credentials_path=credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                )
                self._is_mock = False
            except Exception as e:
                # Fallback silencioso pero informativo
                print(f"[vision_adapter] No se pudo inicializar Google Vision, usando mock: {e!r}")
                self._extractor = DevelopmentTextExtractor(
                    mode=self.mode, language_hints=self.language_hints
                )
                self._is_mock = True
        else:
            if force_mock:
                print("[vision_adapter] USE_MOCK_OCR=1 -> usando mock.")
            elif not GOOGLE_VISION_AVAILABLE:
                print("[vision_adapter] Google Vision no disponible -> usando mock.")
            self._extractor = DevelopmentTextExtractor(
                mode=self.mode, language_hints=self.language_hints
            )
            self._is_mock = True

    # ------------------------------------------------------------------ #
    # Métodos del puerto (delegan al extractor real o mock)
    # ------------------------------------------------------------------ #
    def extract_text(self, image_bytes: bytes) -> str:
        """Extrae texto plano."""
        return self._extractor.extract_text(image_bytes)

    def extract_text_with_mode(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
    ) -> str:
        """Extrae texto indicando un modo concreto (documento, manuscrita, etc.)."""
        return self._extractor.extract_text_with_mode(image_bytes, mode)

    def extract_text_detailed(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None,
    ) -> ExtractionResult:
        """Extrae texto con detalle (confianza, cajas, etc.)."""
        return self._extractor.extract_text_detailed(image_bytes, mode, language_hints)

    def extract_structured_text(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extrae estructura (páginas/bloques/párrafos) si el backend lo soporta."""
        return self._extractor.extract_structured_text(image_bytes, language_hints)

    def validate_image(self, image_bytes: bytes) -> bool:
        """Valida si la imagen es procesable por el backend actual."""
        return self._extractor.validate_image(image_bytes)

    # ------------------------------------------------------------------ #
    # Propiedades auxiliares
    # ------------------------------------------------------------------ #
    @property
    def is_mock(self) -> bool:
        """Indica si el backend actual es el *mock* de desarrollo."""
        return self._is_mock


__all__ = ["TextExtractorAdapter"]
