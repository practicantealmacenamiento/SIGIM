# -*- coding: utf-8 -*-
"""Adaptador OCR con prioridad a Google Vision y fallback a modo mock."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.domain.ports.external_ports import ExtractionMode, ExtractionResult, TextExtractorPort

try:  # Disponibilidad de Google Vision controlada por entorno
    if os.getenv("GCV_DISABLED", "0") in ("1", "true", "True"):
        raise ImportError("Google Vision deshabilitado por flag")
    from app.infrastructure.adapters.external_adapters.vision import GoogleVisionAdapter  # type: ignore

    GOOGLE_VISION_AVAILABLE = True
except Exception:
    GOOGLE_VISION_AVAILABLE = False

from app.infrastructure.adapters.external_adapters.mock_vision import DevelopmentTextExtractor


class TextExtractorAdapter(TextExtractorPort):
    """Implementa TextExtractorPort usando Vision o un mock local."""

    def __init__(
        self,
        *,
        mode: str = "text",
        language_hints: Optional[List[str]] = None,
        credentials_path: Optional[str] = None,
    ) -> None:
        self.mode = (mode or "text").lower()
        self.language_hints = list(language_hints or [])
        self._is_mock = True

        force_mock = os.getenv("USE_MOCK_OCR", "0") in ("1", "true", "True")

        if not force_mock and GOOGLE_VISION_AVAILABLE:
            try:
                self._extractor = GoogleVisionAdapter(  # type: ignore[call-arg]
                    mode=self.mode,
                    language_hints=self.language_hints,
                    credentials_path=credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                )
                self._is_mock = False
            except Exception as exc:  # pragma: no cover - log informativo
                print(f"[vision_adapter] Falla con Google Vision, usando mock: {exc!r}")
                self._extractor = DevelopmentTextExtractor(mode=self.mode, language_hints=self.language_hints)
                self._is_mock = True
        else:
            if force_mock:  # pragma: no cover
                print("[vision_adapter] USE_MOCK_OCR=1 -> usando mock.")
            elif not GOOGLE_VISION_AVAILABLE:  # pragma: no cover
                print("[vision_adapter] Google Vision no disponible -> usando mock.")
            self._extractor = DevelopmentTextExtractor(mode=self.mode, language_hints=self.language_hints)
            self._is_mock = True

    # ------------------------------------------------------------------
    # Implementacion del puerto
    # ------------------------------------------------------------------
    def extract_text(self, image_bytes: bytes) -> str:
        return self._extractor.extract_text(image_bytes)

    def extract_text_with_mode(self, image_bytes: bytes, mode: ExtractionMode = ExtractionMode.TEXT) -> str:
        return self._extractor.extract_text_with_mode(image_bytes, mode)

    def extract_text_detailed(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None,
    ) -> ExtractionResult:
        return self._extractor.extract_text_detailed(image_bytes, mode, language_hints)

    def extract_structured_text(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self._extractor.extract_structured_text(image_bytes, language_hints)

    def validate_image(self, image_bytes: bytes) -> bool:
        return self._extractor.validate_image(image_bytes)

    # ------------------------------------------------------------------
    # Propiedades auxiliares
    # ------------------------------------------------------------------
    @property
    def is_mock(self) -> bool:
        return self._is_mock


__all__ = ["TextExtractorAdapter"]
