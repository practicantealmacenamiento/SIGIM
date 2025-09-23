from __future__ import annotations

from typing import Dict

from app.domain.ports import TextExtractorPort
from app.domain import rules  # canonical_semantic_tag + reglas
from app.domain.exceptions import (
    InvalidImageError,
    ExtractionError,
    EntityNotFoundError,
)

# Mantener aliases para compatibilidad con código existente
InvalidImage = InvalidImageError
ExtractionFailed = ExtractionError


class VerificationService:
    """
    Servicio de verificación OCR desacoplado del proveedor (usa TextExtractorPort).
    Aplica reglas por semantic_tag (ya normalizado a slug canónico).
    """

    def __init__(self, *, text_extractor: TextExtractorPort, question_repo=None):
        self.text_extractor = text_extractor
        self.question_repo = question_repo

    # -------- Flujos específicos (útiles también para test unitario) --------
    def verificar_placa(self, imagen_bytes: bytes) -> Dict:
        texto = self._ocr(imagen_bytes)
        placa = rules.normalizar_placa(texto)
        ok = placa != "NO_DETECTADA"
        return {"ocr_raw": texto, "placa": placa if ok else None, "valido": ok}

    def verificar_precinto(self, imagen_bytes: bytes) -> Dict:
        texto = self._ocr(imagen_bytes)
        precinto = rules.limpiar_precinto(texto)
        ok = precinto not in ("NO DETECTADO", "NO_DETECTADA", None)
        return {"ocr_raw": texto, "precinto": precinto if ok else None, "valido": ok}

    def verificar_contenedor(self, imagen_bytes: bytes) -> Dict:
        texto = self._ocr(imagen_bytes)
        code = rules.extraer_contenedor(texto)
        ok = bool(code) and code != "NO DETECTADO" and rules.validar_iso6346(code)
        return {"ocr_raw": texto, "contenedor": code if ok else None, "valido": ok}

    # -------- Entrada universal desde el endpoint --------
    def verify_with_question(self, question_id, image_file) -> Dict:
        """
        Complete verification flow including question lookup and image processing.
        Handles all business logic for OCR verification.
        """
        # Get question to determine semantic tag
        if not self.question_repo:
            raise ValueError("Question repository must be provided during service initialization")
        
        question = self.question_repo.get(question_id)
        if not question:
            raise EntityNotFoundError(
                message=f"Pregunta con id {question_id} no encontrada",
                entity_type="Question",
                entity_id=str(question_id)
            )
        
        # Prepare image data
        imagen_bytes = self._prepare_image_data(image_file)
        
        # Get semantic tag and perform verification
        tag = getattr(question, "semantic_tag", "") or "none"
        result = self.verificar_universal(tag, imagen_bytes)
        result["semantic_tag"] = tag
        
        return result

    def verificar_universal(self, tag: str, imagen_bytes: bytes) -> Dict:
        """
        Selecciona la regla correcta según semantic_tag (normalizado).
        Retorna dict con `ocr_raw`, campos derivados (placa/precinto/contenedor) y `valido`.
        """
        canon = rules.canonical_semantic_tag(tag)

        if canon == "placa":
            return self.verificar_placa(imagen_bytes)
        if canon == "precinto":
            return self.verificar_precinto(imagen_bytes)
        if canon == "contenedor":
            return self.verificar_contenedor(imagen_bytes)

        # Fallback genérico: solo devuelve texto y si hay algo no vacío.
        texto = self._ocr(imagen_bytes)
        return {"ocr_raw": texto, "valido": bool(texto.strip())}

    # ---------------- Interno ---------------- #
    def _prepare_image_data(self, image_file):
        """Prepare image data for processing."""
        if not image_file:
            raise InvalidImageError(
                message="No se proporcionó ninguna imagen",
                image_format="none"
            )
        
        try:
            if hasattr(image_file, "seek"):
                image_file.seek(0)
        except Exception:
            pass
        
        imagen_bytes = image_file.read()
        if not imagen_bytes:
            raise InvalidImageError(
                message="Imagen vacía",
                image_size=0
            )
        
        return imagen_bytes

    def _ocr(self, imagen_bytes: bytes) -> str:
        if not imagen_bytes:
            raise InvalidImageError(
                message="Imagen vacía.",
                image_size=0
            )
        try:
            texto = self.text_extractor.extract_text(imagen_bytes) or ""
        except Exception as e:
            raise ExtractionError(
                message=f"OCR falló: {e}",
                service_name="text_extractor",
                error_code=type(e).__name__
            ) from e
        return texto.strip()