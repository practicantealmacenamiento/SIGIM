# -*- coding: utf-8 -*-
"""
app/infrastructure/vision.py
----------------------------

Adaptador directo a Google Cloud Vision que cumple `TextExtractorPort`.
Si las librerías de Google no están instaladas, se provee un *mock* mínimo
para que el import y la clase funcionen sin romper (ideal en dev/CI).

Este módulo NO decide si usar mock o real: simplemente expone
`GoogleVisionAdapter`. El selector con *fallback* lo hace `vision_adapter.py`.
"""

from __future__ import annotations

from typing import Optional, Iterable, List, Dict, Any

from app.domain.ports.external_ports import TextExtractorPort, ExtractionMode, ExtractionResult
from app.domain.exceptions import ExtractionError, InvalidImageError

# ========================== NUEVO: imports cuota mensual ==========================
from datetime import datetime
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import transaction
from app.infrastructure.usage_limits import VisionMonthlyUsage
# ================================================================================

# ---------------------------------------------------------------------
# Dependencia opcional a Google Vision.
# Si falla el import, armamos unas clases "mock" compatibles.
# ---------------------------------------------------------------------
try:
    from google.cloud import vision
    from google.oauth2 import service_account
    import google.auth
    from google.api_core import exceptions as google_exceptions
    _GCV_IMPORTED = True
except Exception:
    _GCV_IMPORTED = False

    # ---- Mock mínimo para que la clase funcione sin dependencias ----
    class _MockVisionClient:
        def text_detection(self, **kwargs):
            return _MockResponse()

        def document_text_detection(self, **kwargs):
            return _MockResponse()

    class _MockResponse:
        def __init__(self):
            self.error = None
            self.text_annotations = [_MockAnnotation()]
            self.full_text_annotation = _MockFullTextAnnotation()

    class _MockAnnotation:
        def __init__(self):
            self.description = "MOCK_TEXT_EXTRACTED"
            self.bounding_poly = None

    class _MockFullTextAnnotation:
        def __init__(self):
            self.text = "MOCK_TEXT_EXTRACTED"
            self.pages = []

    class _MockImage:
        def __init__(self, content):
            self.content = content

    # Módulos/miembros falsos con interfaz similar
    vision = type("MockVision", (), {
        "Image": _MockImage,
        "ImageAnnotatorClient": (lambda **kwargs: _MockVisionClient()),
    })()
    google_exceptions = type("MockExceptions", (), {"GoogleAPICallError": Exception})()
    service_account = None
    google = None


# ========================== Helpers cuota mensual ==========================
VISION_MAX_PER_MONTH = int(getattr(settings, "VISION_MAX_PER_MONTH", 1999))
VISION_TZ = ZoneInfo(getattr(settings, "TIME_ZONE", "America/Bogota"))

class MonthlyQuotaExceeded(Exception):
    """Señala que se alcanzó el tope mensual de OCR."""
    pass

def _now_bogota() -> datetime:
    return datetime.now(tz=VISION_TZ)

def _enforce_monthly_quota_db() -> None:
    """
    Aumenta el contador del mes actual (zona Bogotá) de forma atómica
    y lanza MonthlyQuotaExceeded si supera VISION_MAX_PER_MONTH.
    """
    now = _now_bogota()
    y, m = now.year, now.month
    with transaction.atomic():
        row, _ = (
            VisionMonthlyUsage.objects.select_for_update()
            .get_or_create(year=y, month=m, defaults={"count": 0})
        )
        if row.count >= VISION_MAX_PER_MONTH:
            raise MonthlyQuotaExceeded(
                f"Límite mensual de OCR alcanzado ({VISION_MAX_PER_MONTH})."
            )
        row.count += 1
        row.save(update_fields=["count", "updated_at"])
# ================================================================================


class GoogleVisionAdapter(TextExtractorPort):
    """
    Adaptador a Google Cloud Vision (o *mock*, según disponibilidad).
    Cumple `TextExtractorPort`.

    - mode: "text" (TEXT_DETECTION) | "document" (DOCUMENT_TEXT_DETECTION)
    - language_hints: p. ej. ["es", "en"]
    - credentials_path: ruta al JSON de servicio (opcional)

    NOTA: Si el import de GCV falló, se usará el cliente *mock* interno.
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

        # Si no se importó GCV, usamos el cliente mock siempre.
        if not _GCV_IMPORTED:
            self.client = vision.ImageAnnotatorClient()
            return

        # Inicialización con credenciales reales (o por defecto del entorno)
        try:
            if credentials_path:
                creds = service_account.Credentials.from_service_account_file(credentials_path)
                self.client = vision.ImageAnnotatorClient(credentials=creds)
            else:
                creds, _ = google.auth.default()  # puede usar GOOGLE_APPLICATION_CREDENTIALS
                self.client = vision.ImageAnnotatorClient(credentials=creds)
        except Exception as e:
            # Si algo falla, usamos cliente sin credenciales explícitas (puede funcionar con env)
            # o bien el backend subyacente resolverá credenciales implícitas; en local mockeado igual funciona.
            self.client = vision.ImageAnnotatorClient()
            print(f"[GoogleVisionAdapter] WARNING: inicialización con fallback ({e!r})")

    # ------------------------------------------------------------------ #
    # Métodos del puerto
    # ------------------------------------------------------------------ #
    def extract_text(self, image_bytes: bytes) -> str:
        """Extrae texto plano con el modo actual."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Imagen inválida o vacía",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )
        try:
            _enforce_monthly_quota_db()   # <-- NUEVO: tope mensual
            return self._extract_text_internal(image_bytes, self.mode)
        except MonthlyQuotaExceeded as e:  # <-- NUEVO: mapeo a ExtractionError
            raise ExtractionError(
                message=str(e),
                service_name="GoogleVision",
                error_code="MONTHLY_QUOTA_EXCEEDED",
            )
        except (ExtractionError, InvalidImageError):
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Error inesperado extrayendo texto: {e}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR",
            )

    def extract_text_with_mode(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
    ) -> str:
        """Extrae texto indicando un modo concreto (texto/documento)."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Imagen inválida o vacía",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )
        try:
            _enforce_monthly_quota_db()   # <-- NUEVO
            mode_str = self._map_extraction_mode(mode)
            return self._extract_text_internal(image_bytes, mode_str)
        except MonthlyQuotaExceeded as e:  # <-- NUEVO
            raise ExtractionError(
                message=str(e),
                service_name="GoogleVision",
                error_code="MONTHLY_QUOTA_EXCEEDED",
            )
        except (ExtractionError, InvalidImageError):
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Error inesperado con modo {mode.value}: {e}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR",
            )

    def extract_text_detailed(
        self,
        image_bytes: bytes,
        mode: ExtractionMode = ExtractionMode.TEXT,
        language_hints: Optional[List[str]] = None,
    ) -> ExtractionResult:
        """Extrae texto + *metadata* (confianza, cajas, etc.)."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Imagen inválida o vacía",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )
        try:
            _enforce_monthly_quota_db()   # <-- NUEVO
            mode_str = self._map_extraction_mode(mode)
            hints = language_hints or self.language_hints

            image = vision.Image(content=image_bytes)
            kwargs = {"image_context": {"language_hints": hints}} if hints else {}

            if mode_str == "document":
                response = self.client.document_text_detection(image=image, **kwargs)
            else:
                response = self.client.text_detection(image=image, **kwargs)

            if getattr(response, "error", None) and getattr(response.error, "message", ""):
                raise ExtractionError(
                    message=f"Google Vision API error: {response.error.message}",
                    service_name="GoogleVision",
                    error_code=str(getattr(response.error, "code", "API_ERROR")),
                )

            text = ""
            confidence = None
            bounding_boxes: List[Dict[str, Any]] = []

            if getattr(response, "text_annotations", None):
                # El primer annotation suele contener el texto completo
                text = response.text_annotations[0].description or ""
                for ann in response.text_annotations:
                    if getattr(ann, "bounding_poly", None):
                        vertices = []
                        for v in ann.bounding_poly.vertices:
                            vertices.append({"x": getattr(v, "x", None), "y": getattr(v, "y", None)})
                        bounding_boxes.append({"text": ann.description, "vertices": vertices})

            return ExtractionResult(
                text=text.strip(),
                confidence=confidence,
                bounding_boxes=bounding_boxes,
                metadata={"mode": mode_str, "language_hints": hints},
            )
        except MonthlyQuotaExceeded as e:  # <-- NUEVO
            raise ExtractionError(
                message=str(e),
                service_name="GoogleVision",
                error_code="MONTHLY_QUOTA_EXCEEDED",
            )
        except (ExtractionError, InvalidImageError):
            raise
        except Exception as e:
            # Si tenemos el módulo real, distinguimos errores de API
            if _GCV_IMPORTED and "google_exceptions" in globals() and isinstance(e, getattr(google_exceptions, "GoogleAPICallError", Exception)):
                raise ExtractionError(
                    message=f"Google Vision API call failed: {e}",
                    service_name="GoogleVision",
                    error_code=getattr(getattr(e, "code", None), "name", "API_CALL_ERROR"),
                )
            raise ExtractionError(
                message=f"Error inesperado en extracción detallada: {e}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR",
            )

    def extract_structured_text(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extrae estructura (páginas/bloques/párrafos/palabras)."""
        if not self.validate_image(image_bytes):
            raise InvalidImageError(
                message="Imagen inválida o vacía",
                image_format="unknown",
                image_size=len(image_bytes) if image_bytes else 0,
            )
        try:
            _enforce_monthly_quota_db()
            hints = language_hints or self.language_hints
            image = vision.Image(content=image_bytes)
            kwargs = {"image_context": {"language_hints": hints}} if hints else {}

            response = self.client.document_text_detection(image=image, **kwargs)
            if getattr(response, "error", None) and getattr(response.error, "message", ""):
                raise ExtractionError(
                    message=f"Google Vision API error: {response.error.message}",
                    service_name="GoogleVision",
                    error_code=str(getattr(response.error, "code", "API_ERROR")),
                )

            result: Dict[str, Any] = {
                "full_text": "",
                "pages": [],
                "blocks": [],
                "paragraphs": [],
                "words": [],
            }

            fta = getattr(response, "full_text_annotation", None)
            if fta:
                result["full_text"] = getattr(fta, "text", "") or ""
                for page in getattr(fta, "pages", []):
                    page_data = {"blocks": []}
                    for block in getattr(page, "blocks", []):
                        block_data = {"paragraphs": [], "confidence": getattr(block, "confidence", None)}
                        for paragraph in getattr(block, "paragraphs", []):
                            paragraph_data = {"words": [], "confidence": getattr(paragraph, "confidence", None)}
                            for word in getattr(paragraph, "words", []):
                                symbols = getattr(word, "symbols", [])
                                word_text = "".join([getattr(s, "text", "") for s in symbols])
                                paragraph_data["words"].append({
                                    "text": word_text,
                                    "confidence": getattr(word, "confidence", None),
                                })
                                result["words"].append(word_text)
                            block_data["paragraphs"].append(paragraph_data)
                            result["paragraphs"].append(paragraph_data)
                        page_data["blocks"].append(block_data)
                        result["blocks"].append(block_data)
                    result["pages"].append(page_data)

            return result
        except MonthlyQuotaExceeded as e:
            raise ExtractionError(
                message=str(e),
                service_name="GoogleVision",
                error_code="MONTHLY_QUOTA_EXCEEDED",
            )
        except (ExtractionError, InvalidImageError):
            raise
        except Exception as e:
            if _GCV_IMPORTED and "google_exceptions" in globals() and isinstance(e, getattr(google_exceptions, "GoogleAPICallError", Exception)):
                raise ExtractionError(
                    message=f"Google Vision API call failed: {e}",
                    service_name="GoogleVision",
                    error_code=getattr(getattr(e, "code", None), "name", "API_CALL_ERROR"),
                )
            raise ExtractionError(
                message=f"Error inesperado en extracción estructurada: {e}",
                service_name="GoogleVision",
                error_code="EXTRACTION_ERROR",
            )

    # ------------------------------------------------------------------ #
    # Validación y utilidades internas
    # ------------------------------------------------------------------ #
    def validate_image(self, image_bytes: bytes) -> bool:
        """Chequeo rápido de magia de archivo (JPG/PNG/GIF/WebP/BMP)."""
        if not image_bytes:
            return False
        signatures = [
            b"\xff\xd8\xff",           # JPEG
            b"\x89PNG\r\n\x1a\n",      # PNG
            b"GIF87a",                 # GIF87a
            b"GIF89a",                 # GIF89a
            b"RIFF",                   # WebP (RIFF)
            b"BM",                     # BMP
        ]
        return any(image_bytes.startswith(sig) for sig in signatures)

    def _extract_text_internal(self, image_bytes: bytes, mode: str) -> str:
        """Implementación base para *text* o *document*."""
        image = vision.Image(content=image_bytes)
        kwargs = {"image_context": {"language_hints": self.language_hints}} if self.language_hints else {}

        try:
            if mode == "document":
                response = self.client.document_text_detection(image=image, **kwargs)
                if getattr(response, "error", None) and getattr(response.error, "message", ""):
                    raise ExtractionError(
                        message=f"GCV document error: {response.error.message}",
                        service_name="GoogleVision",
                        error_code=str(getattr(response.error, "code", "DOCUMENT_DETECTION_ERROR")),
                    )
                text = (getattr(getattr(response, "full_text_annotation", None), "text", "") or "")
                if not text and getattr(response, "text_annotations", None):
                    text = response.text_annotations[0].description or ""
                return text.strip()

            # Default: TEXT_DETECTION
            response = self.client.text_detection(image=image, **kwargs)
            if getattr(response, "error", None) and getattr(response.error, "message", ""):
                raise ExtractionError(
                    message=f"GCV text error: {response.error.message}",
                    service_name="GoogleVision",
                    error_code=str(getattr(response.error, "code", "TEXT_DETECTION_ERROR")),
                )
            anns = getattr(response, "text_annotations", []) or []
            return (anns[0].description.strip() if anns else "")
        except ExtractionError:
            raise
        except Exception as e:
            if _GCV_IMPORTED and "google_exceptions" in globals() and isinstance(e, getattr(google_exceptions, "GoogleAPICallError", Exception)):
                raise ExtractionError(
                    message=f"Google Vision API call failed: {e}",
                    service_name="GoogleVision",
                    error_code=getattr(getattr(e, "code", None), "name", "API_CALL_ERROR"),
                )
            raise ExtractionError(
                message=f"Error interno en extracción: {e}",
                service_name="GoogleVision",
                error_code="INTERNAL_ERROR",
            )

    def _map_extraction_mode(self, mode: ExtractionMode) -> str:
        """Traduce ExtractionMode a cadena interna."""
        if mode == ExtractionMode.DOCUMENT or mode == ExtractionMode.HANDWRITING:
            return "document"
        return "text"
