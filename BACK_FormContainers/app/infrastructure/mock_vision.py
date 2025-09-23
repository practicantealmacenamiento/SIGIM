"""
Mock Text Extractor for Development

This module provides a mock implementation of TextExtractorPort that can be used
for development and testing when Google Cloud Vision is not available.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
import re

from app.domain.ports import TextExtractorPort, ExtractionMode, ExtractionResult
from app.domain.exceptions import ExtractionError, InvalidImageError


class MockTextExtractor(TextExtractorPort):
    """
    Mock text extractor that simulates OCR functionality for development.
    
    This adapter provides realistic mock responses based on common OCR patterns
    and can be used for testing business logic without requiring external services.
    """

    def __init__(self, *, mode: str = "text", language_hints: Optional[List[str]] = None):
        self.mode = (mode or "text").lower()
        self.language_hints = list(language_hints or [])

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract mock text from image bytes."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Invalid image format or empty image data",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0
            )
        
        # Generate mock text based on image size to simulate realistic behavior
        image_size = len(image_bytes)
        
        if image_size < 1000:
            return "ABC123"  # Small image, simple text
        elif image_size < 10000:
            return "PLACA ABC123 CONTENEDOR MSCU1234567"  # Medium image
        else:
            return "DOCUMENTO TRANSPORTE\nPLACA: ABC123\nCONTENEDOR: MSCU1234567\nPRECINTO: TDM38816"

    def extract_text_with_mode(
        self, 
        image_bytes: bytes, 
        mode: ExtractionMode = ExtractionMode.TEXT
    ) -> str:
        """Extract text using a specific extraction mode."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Invalid image format or empty image data",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0
            )
        
        base_text = self.extract_text(image_bytes)
        
        if mode == ExtractionMode.DOCUMENT:
            # Document mode returns more structured text
            return f"DOCUMENTO OFICIAL\n{base_text}\nFECHA: 2024-01-15"
        elif mode == ExtractionMode.HANDWRITING:
            # Handwriting mode might have lower accuracy
            return base_text.replace("123", "1Z3").replace("ABC", "A8C")
        else:
            return base_text

    def extract_text_detailed(
        self, 
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None
    ) -> ExtractionResult:
        """Extract text with detailed information including confidence and location."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Invalid image format or empty image data",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0
            )
        
        text = self.extract_text_with_mode(image_bytes, mode)
        
        # Mock bounding boxes
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
                    {"x": x_offset, "y": 30}
                ]
            })
            x_offset += len(word) * 8 + 5
        
        return ExtractionResult(
            text=text,
            confidence=0.95,  # Mock high confidence
            bounding_boxes=bounding_boxes,
            metadata={
                "mode": mode.value,
                "language_hints": language_hints or self.language_hints,
                "mock": True
            }
        )

    def extract_structured_text(
        self, 
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extract structured text for complex documents."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Invalid image format or empty image data",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0
            )
        
        text = self.extract_text(image_bytes)
        words = text.split()
        
        return {
            "full_text": text,
            "pages": [{
                "blocks": [{
                    "paragraphs": [{
                        "words": [{"text": word, "confidence": 0.95} for word in words],
                        "confidence": 0.95
                    }],
                    "confidence": 0.95
                }]
            }],
            "blocks": [{
                "paragraphs": [{
                    "words": [{"text": word, "confidence": 0.95} for word in words],
                    "confidence": 0.95
                }],
                "confidence": 0.95
            }],
            "paragraphs": [{
                "words": [{"text": word, "confidence": 0.95} for word in words],
                "confidence": 0.95
            }],
            "words": words
        }

    def validate_image(self, image_bytes: bytes) -> bool:
        """Validate if an image is processable by the OCR service."""
        if not image_bytes or len(image_bytes) == 0:
            return False
        
        # Basic validation - check if it looks like image data
        # Most image formats start with specific magic bytes
        image_signatures = [
            b'\xff\xd8\xff',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'GIF87a',  # GIF87a
            b'GIF89a',  # GIF89a
            b'RIFF',  # WebP (starts with RIFF)
            b'BM',  # BMP
        ]
        
        for signature in image_signatures:
            if image_bytes.startswith(signature):
                return True
        
        # For mock purposes, also accept any non-empty bytes
        return len(image_bytes) > 0


class DevelopmentTextExtractor(MockTextExtractor):
    """
    Development-specific text extractor with predefined responses.
    
    This extractor provides specific mock responses that are useful for
    testing business rules and validation logic.
    """

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text with development-specific patterns."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Invalid image format or empty image data",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0
            )
        
        # Use image size as a simple hash to return different mock responses
        image_size = len(image_bytes)
        
        responses = [
            "ABC123",  # Valid plate
            "MSCU1234567",  # Valid container
            "TDM38816",  # Valid seal
            "PLACA ABC123 CONTENEDOR MSCU1234567",  # Multiple elements
            "DOCUMENTO TRANSPORTE\nPLACA: DEF456\nCONTENEDOR: TCLU9876543\nPRECINTO: XYZ12345",
            "INVALID TEXT NO PATTERNS",  # No valid patterns
            "123456789",  # Numbers only
            "ABCDEFGH",  # Letters only
        ]
        
        return responses[image_size % len(responses)]