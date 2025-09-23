"""
Servicio de verificación mejorado con mejor detección de precintos
y capacidades de debugging/logging.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import logging

from app.domain.ports import TextExtractorPort
from app.domain import rules
from app.domain.precinto_simple import get_precinto_info_simple
from app.application.verification import VerificationService, InvalidImage, ExtractionFailed

logger = logging.getLogger(__name__)


class EnhancedVerificationService(VerificationService):
    """
    Servicio de verificación mejorado que extiende el original
    con mejor detección de precintos y capacidades de debugging.
    """

    def __init__(self, text_extractor: TextExtractorPort, debug_mode: bool = False):
        super().__init__(text_extractor)
        self.debug_mode = debug_mode

    def verificar_precinto(self, imagen_bytes: bytes) -> Dict:
        """
        Verificación mejorada de precintos con información detallada.
        """
        texto = self._ocr(imagen_bytes)
        
        if self.debug_mode:
            logger.info(f"OCR texto extraído: '{texto}'")
        
        # Usar el detector simplificado y optimizado
        detection_info = get_precinto_info_simple(texto)
        
        precinto = detection_info["precinto"]
        ok = precinto not in ("NO DETECTADO", "NO_DETECTADA", None)
        
        result = {
            "ocr_raw": texto,
            "precinto": precinto if ok else None,
            "valido": ok
        }
        
        # Agregar información de debugging si está habilitado
        if self.debug_mode:
            result["debug_info"] = {
                "confianza": detection_info.get("confianza", 0.0),
                "candidatos": detection_info.get("candidatos", []),
                "razon": detection_info.get("razon", "unknown"),
                "texto_normalizado": texto.strip().upper() if texto else "",
                "texto_limpio": detection_info.get("texto_limpio", "")
            }
            logger.info(f"Detección de precinto: {result['debug_info']}")
        
        return result

    def verificar_universal(self, tag: str, imagen_bytes: bytes) -> Dict:
        """
        Verificación universal mejorada con información adicional.
        """
        canon = rules.canonical_semantic_tag(tag)
        
        if canon == "precinto":
            return self.verificar_precinto(imagen_bytes)
        
        # Para otros tipos, usar la implementación base
        return super().verificar_universal(tag, imagen_bytes)

    def verificar_con_metadatos(self, tag: str, imagen_bytes: bytes) -> Dict:
        """
        Verificación que siempre incluye metadatos detallados,
        útil para análisis y mejora del sistema.
        """
        # Temporalmente habilitar debug para esta verificación
        debug_original = self.debug_mode
        self.debug_mode = True
        
        try:
            result = self.verificar_universal(tag, imagen_bytes)
            
            # Agregar metadatos generales
            result["metadata"] = {
                "semantic_tag": tag,
                "canonical_tag": rules.canonical_semantic_tag(tag),
                "ocr_length": len(result.get("ocr_raw", "")),
                "has_letters": bool(result.get("ocr_raw", "")) and any(c.isalpha() for c in result.get("ocr_raw", "")),
                "has_numbers": bool(result.get("ocr_raw", "")) and any(c.isdigit() for c in result.get("ocr_raw", "")),
            }
            
            return result
            
        finally:
            self.debug_mode = debug_original


def create_verification_service(text_extractor: TextExtractorPort, 
                              enhanced: bool = True, 
                              debug: bool = False) -> VerificationService:
    """
    Factory para crear el servicio de verificación apropiado.
    
    Args:
        text_extractor: Adaptador de extracción de texto
        enhanced: Si usar la versión mejorada (recomendado)
        debug: Si habilitar modo debug
    
    Returns:
        Instancia del servicio de verificación
    """
    if enhanced:
        return EnhancedVerificationService(text_extractor, debug_mode=debug)
    else:
        return VerificationService(text_extractor)
