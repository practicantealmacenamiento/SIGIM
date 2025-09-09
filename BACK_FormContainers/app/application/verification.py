from __future__ import annotations

from typing import Dict

from app.domain.ports import TextExtractorPort
from app.domain import rules  # canonical_semantic_tag + reglas


class InvalidImage(Exception):
    """La imagen es inválida (vacía, corrupta o tipo no soportado)."""


class ExtractionFailed(Exception):
    """El OCR falló por un problema externo (servicio, credenciales, red, etc.)."""


class VerificationService:
    """
    Servicio de verificación OCR desacoplado del proveedor (usa TextExtractorPort).
    Aplica reglas por semantic_tag (ya normalizado a slug canónico).
    """

    def __init__(self, text_extractor: TextExtractorPort):
        self.text_extractor = text_extractor

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
    def _ocr(self, imagen_bytes: bytes) -> str:
        if not imagen_bytes:
            raise InvalidImage("Imagen vacía.")
        try:
            texto = self.text_extractor.extract_text(imagen_bytes) or ""
        except Exception as e:
            raise ExtractionFailed(f"OCR falló: {e}") from e
        return texto.strip()