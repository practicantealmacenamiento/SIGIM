"""
Vision Adapter with Graceful Fallback

This module provides a text extraction adapter that gracefully handles
the case where Google Cloud Vision is not available by falling back to
a mock implementation.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from app.domain.ports import TextExtractorPort, ExtractionMode, ExtractionResult
from app.domain.exceptions import ExtractionError, InvalidImageError

# Try to import Google Vision, fall back to mock if not available
try:
    from app.infrastructure.vision import GoogleVisionAdapter
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

# Always import the mock extractor for fallback
from app.infrastructure.mock_vision import DevelopmentTextExtractor


class TextExtractorAdapter(TextExtractorPort):
    """
    Text extractor adapter that uses Google Vision when available,
    falls back to mock implementation for development.
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
        
        if GOOGLE_VISION_AVAILABLE:
            try:
                self._extractor = GoogleVisionAdapter(
                    mode=mode,
                    language_hints=language_hints,
                    credentials_path=credentials_path
                )
                self._is_mock = False
            except Exception as e:
                print(f"Warning: Failed to initialize Google Vision, using mock: {e}")
                self._extractor = DevelopmentTextExtractor(
                    mode=mode,
                    language_hints=language_hints
                )
                self._is_mock = True
        else:
            print("Warning: Google Cloud Vision not available, using mock text extractor")
            self._extractor = DevelopmentTextExtractor(
                mode=mode,
                language_hints=language_hints
            )
            self._is_mock = True

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract basic text from image bytes."""
        return self._extractor.extract_text(image_bytes)

    def extract_text_with_mode(
        self, 
        image_bytes: bytes, 
        mode: ExtractionMode = ExtractionMode.TEXT
    ) -> str:
        """Extract text using a specific extraction mode."""
        return self._extractor.extract_text_with_mode(image_bytes, mode)

    def extract_text_detailed(
        self, 
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None
    ) -> ExtractionResult:
        """Extract text with detailed information including confidence and location."""
        return self._extractor.extract_text_detailed(image_bytes, mode, language_hints)

    def extract_structured_text(
        self, 
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extract structured text for complex documents."""
        return self._extractor.extract_structured_text(image_bytes, language_hints)

    def validate_image(self, image_bytes: bytes) -> bool:
        """Validate if an image is processable by the OCR service."""
        return self._extractor.validate_image(image_bytes)

    @property
    def is_mock(self) -> bool:
        """Return True if using mock implementation."""
        return self._is_mock