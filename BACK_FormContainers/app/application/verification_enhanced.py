"""Servicio de verificación con modo de depuración para precintos."""

from __future__ import annotations

from typing import Dict

from app.application.verification import VerificationService
from app.domain import rules
from app.domain.precinto_rules import get_precinto_detection_info, limpiar_precinto_mejorado

__all__ = ["EnhancedVerificationService"]


class EnhancedVerificationService(VerificationService):
    """Extiende el servicio estándar con información detallada para precintos."""

    def __init__(self, *args, debug_mode: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_mode = debug_mode

    def verificar_precinto(self, imagen_bytes: bytes) -> Dict:
        texto = self._ocr(imagen_bytes)
        info = get_precinto_detection_info(texto)
        precinto = info["precinto"]
        ok = precinto not in ("NO DETECTADO", "NO_DETECTADA", None)

        resultado = {
            "ocr_raw": texto,
            "precinto": precinto if ok else None,
            "valido": ok,
        }

        if self.debug_mode:
            resultado["detalles"] = info

        return resultado

    def verificar_universal(self, tag: str, imagen_bytes: bytes) -> Dict:
        canon = rules.canonical_semantic_tag(tag)
        if canon == "precinto":
            return self.verificar_precinto(imagen_bytes)
        if canon == "placa":
            texto = self._ocr(imagen_bytes)
            placa = rules.normalizar_placa(texto)
            ok = placa != "NO_DETECTADA"
            return {"ocr_raw": texto, "placa": placa if ok else None, "valido": ok}
        if canon == "contenedor":
            texto = self._ocr(imagen_bytes)
            code = rules.extraer_contenedor(texto)
            ok = bool(code) and code != "NO DETECTADO" and rules.validar_iso6346(code)
            return {"ocr_raw": texto, "contenedor": code if ok else None, "valido": ok}

        texto = self._ocr(imagen_bytes)
        return {"ocr_raw": texto, "valido": bool(texto.strip())}

    def limpiar_precinto(self, texto: str) -> str:
        """Helper para compatibilidad externa (usa la versión mejorada)."""

        return limpiar_precinto_mejorado(texto)

