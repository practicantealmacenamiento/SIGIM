from __future__ import annotations

from typing import Optional, Iterable, List, Dict, Any

from app.domain.ports import TextExtractorPort, ExtractionMode, ExtractionResult
from app.domain.exceptions import ExtractionError, InvalidImageError

# Try to import Google Cloud Vision, fall back to mock if not available
try:
    from google.cloud import vision
    from google.oauth2 import service_account
    import google.auth
    from google.api_core import exceptions as google_exceptions
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    # Mock classes for development
    class MockVisionClient:
        def text_detection(self, **kwargs):
            return MockResponse()
        def document_text_detection(self, **kwargs):
            return MockResponse()
    
    class MockResponse:
        def __init__(self):
            self.error = None
            self.text_annotations = [MockAnnotation()]
            self.full_text_annotation = MockFullTextAnnotation()
    
    class MockAnnotation:
        def __init__(self):
            self.description = "MOCK_TEXT_EXTRACTED"
            self.bounding_poly = None
    
    class MockFullTextAnnotation:
        def __init__(self):
            self.text = "MOCK_TEXT_EXTRACTED"
            self.pages = []
    
    class MockImage:
        def __init__(self, content):
            self.content = content
    
    # Mock the modules
    vision = type('MockVision', (), {
        'Image': MockImage,
        'ImageAnnotatorClient': lambda **kwargs: MockVisionClient()
    })()
    google_exceptions = type('MockExceptions', (), {
        'GoogleAPICallError': Exception
    })()
    service_account = None
    google = None


class GoogleVisionAdapter(TextExtractorPort):
    """
    Adaptador a Google Cloud Vision para cumplir TextExtractorPort.
    - mode: "text" (TEXT_DETECTION) | "document" (DOCUMENT_TEXT_DETECTION)
    - language_hints: lista opcional (p. ej., ["es", "en"])
    - credentials: ruta a archivo json o credenciales automáticas de entorno
    """

    def __init__(
        self,
        *,
        mode: str = "text",
        language_hints: Optional[Iterable[str]] = None,
        credentials_path: Optional[str] = None,
    ):
        self.mode = (mode or "text").lower()
        self.language_hints = list(language_hints or [])

        if not GOOGLE_VISION_AVAILABLE:
            # Use mock client for development
            self.client = vision.ImageAnnotatorClient()
            return

        try:
            if credentials_path:
                creds = service_account.Credentials.from_service_account_file(credentials_path)
            else:
                creds, _ = google.auth.default()

            self.client = vision.ImageAnnotatorClient(credentials=creds)
        except Exception as e:
            # Fall back to mock client if credentials fail
            self.client = vision.ImageAnnotatorClient()
            print(f"Warning: Using mock Google Vision client due to initialization error: {e}")

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract basic text from image bytes using the configured mode."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Invalid image format or empty image data",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0
            )
        
        try:
            return self._extract_text_internal(image_bytes, self.mode)
        except (ExtractionError, InvalidImageError):
            # Re-raise domain exceptions as-is
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Unexpected error during text extraction: {str(e)}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR"
            )

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
        
        try:
            mode_str = self._map_extraction_mode(mode)
            return self._extract_text_internal(image_bytes, mode_str)
        except (ExtractionError, InvalidImageError):
            # Re-raise domain exceptions as-is
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Unexpected error during text extraction with mode {mode.value}: {str(e)}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR"
            )

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
        
        try:
            mode_str = self._map_extraction_mode(mode)
            hints = language_hints or self.language_hints
            
            image = vision.Image(content=image_bytes)
            kwargs = {}
            if hints:
                kwargs["image_context"] = {"language_hints": hints}

            if mode_str == "document":
                response = self.client.document_text_detection(image=image, **kwargs)
            else:
                response = self.client.text_detection(image=image, **kwargs)

            if response.error and response.error.message:
                raise ExtractionError(
                    message=f"Google Vision API error: {response.error.message}",
                    service_name="GoogleVision",
                    error_code=str(response.error.code) if response.error.code else "API_ERROR"
                )

            text = ""
            confidence = None
            bounding_boxes = []
            
            if response.text_annotations:
                # First annotation contains the full text
                text = response.text_annotations[0].description or ""
                
                # Extract bounding boxes and confidence from all annotations
                for annotation in response.text_annotations:
                    if annotation.bounding_poly:
                        vertices = []
                        for vertex in annotation.bounding_poly.vertices:
                            vertices.append({"x": vertex.x, "y": vertex.y})
                        bounding_boxes.append({
                            "text": annotation.description,
                            "vertices": vertices
                        })

            return ExtractionResult(
                text=text.strip(),
                confidence=confidence,
                bounding_boxes=bounding_boxes,
                metadata={"mode": mode_str, "language_hints": hints}
            )
        except (ExtractionError, InvalidImageError):
            # Re-raise domain exceptions as-is
            raise
        except google_exceptions.GoogleAPICallError as e:
            raise ExtractionError(
                message=f"Google Vision API call failed: {str(e)}",
                service_name="GoogleVision",
                error_code=e.code.name if hasattr(e, 'code') else "API_CALL_ERROR"
            )
        except Exception as e:
            raise ExtractionError(
                message=f"Unexpected error during detailed text extraction: {str(e)}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR"
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
        
        try:
            hints = language_hints or self.language_hints
            
            image = vision.Image(content=image_bytes)
            kwargs = {}
            if hints:
                kwargs["image_context"] = {"language_hints": hints}

            response = self.client.document_text_detection(image=image, **kwargs)
            
            if response.error and response.error.message:
                raise ExtractionError(
                    message=f"Google Vision API error: {response.error.message}",
                    service_name="GoogleVision",
                    error_code=str(response.error.code) if response.error.code else "API_ERROR"
                )

            result = {
                "full_text": "",
                "pages": [],
                "blocks": [],
                "paragraphs": [],
                "words": []
            }

            if response.full_text_annotation:
                result["full_text"] = response.full_text_annotation.text or ""
                
                for page in response.full_text_annotation.pages:
                    page_data = {"blocks": []}
                    
                    for block in page.blocks:
                        block_data = {
                            "paragraphs": [],
                            "confidence": getattr(block, 'confidence', None)
                        }
                        
                        for paragraph in block.paragraphs:
                            paragraph_data = {
                                "words": [],
                                "confidence": getattr(paragraph, 'confidence', None)
                            }
                            
                            for word in paragraph.words:
                                word_text = "".join([symbol.text for symbol in word.symbols])
                                paragraph_data["words"].append({
                                    "text": word_text,
                                    "confidence": getattr(word, 'confidence', None)
                                })
                                result["words"].append(word_text)
                            
                            block_data["paragraphs"].append(paragraph_data)
                            result["paragraphs"].append(paragraph_data)
                        
                        page_data["blocks"].append(block_data)
                        result["blocks"].append(block_data)
                    
                    result["pages"].append(page_data)

            return result
        except (ExtractionError, InvalidImageError):
            # Re-raise domain exceptions as-is
            raise
        except google_exceptions.GoogleAPICallError as e:
            raise ExtractionError(
                message=f"Google Vision API call failed: {str(e)}",
                service_name="GoogleVision",
                error_code=e.code.name if hasattr(e, 'code') else "API_CALL_ERROR"
            )
        except Exception as e:
            raise ExtractionError(
                message=f"Unexpected error during structured text extraction: {str(e)}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR"
            )

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
        
        return False

    def _extract_text_internal(self, image_bytes: bytes, mode: str) -> str:
        """Internal method to extract text with specified mode."""
        try:
            image = vision.Image(content=image_bytes)
            kwargs = {}
            if self.language_hints:
                kwargs["image_context"] = {"language_hints": self.language_hints}

            if mode == "document":
                response = self.client.document_text_detection(image=image, **kwargs)
                if response.error and response.error.message:
                    raise ExtractionError(
                        message=f"Google Vision document detection error: {response.error.message}",
                        service_name="GoogleVision",
                        error_code=str(response.error.code) if response.error.code else "DOCUMENT_DETECTION_ERROR"
                    )
                text = (response.full_text_annotation.text if response.full_text_annotation else "") or ""
                if not text and response.text_annotations:
                    text = response.text_annotations[0].description or ""
                return text.strip()

            # Default: mode == "text"
            response = self.client.text_detection(image=image, **kwargs)
            if response.error and response.error.message:
                raise ExtractionError(
                    message=f"Google Vision text detection error: {response.error.message}",
                    service_name="GoogleVision",
                    error_code=str(response.error.code) if response.error.code else "TEXT_DETECTION_ERROR"
                )
            anns = response.text_annotations or []
            return (anns[0].description.strip() if anns else "")
        except ExtractionError:
            # Re-raise domain exceptions as-is
            raise
        except google_exceptions.GoogleAPICallError as e:
            raise ExtractionError(
                message=f"Google Vision API call failed: {str(e)}",
                service_name="GoogleVision",
                error_code=e.code.name if hasattr(e, 'code') else "API_CALL_ERROR"
            )
        except Exception as e:
            raise ExtractionError(
                message=f"Unexpected error during internal text extraction: {str(e)}",
                service_name="GoogleVision",
                error_code="INTERNAL_ERROR"
            )

    def _map_extraction_mode(self, mode: ExtractionMode) -> str:
        """Map ExtractionMode enum to internal mode string."""
        if mode == ExtractionMode.DOCUMENT:
            return "document"
        elif mode == ExtractionMode.HANDWRITING:
            return "document"  # Use document mode for handwriting
        else:
            return "text"
