from __future__ import annotations

from typing import Optional, Iterable

from google.cloud import vision
from google.oauth2 import service_account
import google.auth

from app.domain.ports import TextExtractorPort


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

        if credentials_path:
            creds = service_account.Credentials.from_service_account_file(credentials_path)
        else:
            creds, _ = google.auth.default()

        self.client = vision.ImageAnnotatorClient(credentials=creds)

    def extract_text(self, image_bytes: bytes) -> str:
        image = vision.Image(content=image_bytes)
        kwargs = {}
        if self.language_hints:
            kwargs["image_context"] = {"language_hints": self.language_hints}

        if self.mode == "document":
            response = self.client.document_text_detection(image=image, **kwargs)
            if response.error and response.error.message:
                raise RuntimeError(f"Google Vision (document) error: {response.error.message}")
            text = (response.full_text_annotation.text if response.full_text_annotation else "") or ""
            if not text and response.text_annotations:
                text = response.text_annotations[0].description or ""
            return text.strip()

        # Default: mode == "text"
        response = self.client.text_detection(image=image, **kwargs)
        if response.error and response.error.message:
            raise RuntimeError(f"Google Vision (text) error: {response.error.message}")
        anns = response.text_annotations or []
        return (anns[0].description.strip() if anns else "")
