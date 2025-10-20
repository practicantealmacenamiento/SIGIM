# -*- coding: utf-8 -*-
"""
Servicio de verificación OCR desacoplado del proveedor.

Responsabilidades:
- Orquestar la extracción de texto (vía `TextExtractorPort`).
- Aplicar reglas específicas según `semantic_tag` canónico:
    * placa          → `rules.normalizar_placa`
    * precinto       → `rules.limpiar_precinto`
    * contenedor ISO → `rules.extraer_contenedor` + `rules.validar_iso6346`
- Exponer flujos especializados (`verificar_placa/precinto/contenedor`) y un
  flujo universal (`verificar_universal`) que enruta por `semantic_tag`.
- Proveer un flujo de “end-to-end” `verify_with_question` que consulta la
  pregunta por id y procesa la imagen recibida.

Notas:
- Este servicio no conoce detalles de infraestructura (ORM, frameworks).
- Los métodos retornan dicts planos listos para serializar en la capa de
  interfaces.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from typing import Dict, Any, Optional

# ── Puertos / Dominio ─────────────────────────────────────────────────────────
from app.domain import rules  # canonical_semantic_tag + reglas
from app.domain.ports import TextExtractorPort
from app.domain.exceptions import (
    EntityNotFoundError,
    ExtractionError,
    InvalidImageError,
)

# Mantener aliases para compatibilidad con código existente
InvalidImage = InvalidImageError
ExtractionFailed = ExtractionError

__all__ = [
    "VerificationService",
    "InvalidImage",       # alias de compatibilidad
    "ExtractionFailed",   # alias de compatibilidad
]


class VerificationService:
    """
    Servicio de verificación OCR desacoplado del proveedor (usa `TextExtractorPort`).

    Aplica reglas por `semantic_tag` (normalizado a slug canónico).
    """

    def __init__(self, *, text_extractor: TextExtractorPort, question_repo=None):
        """
        Args:
            text_extractor: Implementación del puerto de OCR.
            question_repo: Repositorio de preguntas (opcional), requerido por `verify_with_question`.
        """
        self.text_extractor = text_extractor
        self.question_repo = question_repo

    # ==========================================================================
    #   Flujos específicos (útiles también para test unitario)
    # ==========================================================================

    def verificar_placa(self, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Verifica y normaliza una placa colombiana a partir del OCR.
        Retorna: {"ocr_raw": str, "placa": str|None, "valido": bool}
        """
        texto = self._ocr(imagen_bytes)
        placa = rules.normalizar_placa(texto)
        ok = placa != "NO_DETECTADA"
        return {"ocr_raw": texto, "placa": placa if ok else None, "valido": ok}

    def verificar_precinto(self, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Extrae un precinto alfanumérico robusto desde el OCR.
        Retorna: {"ocr_raw": str, "precinto": str|None, "valido": bool}
        """
        texto = self._ocr(imagen_bytes)
        precinto = rules.limpiar_precinto(texto)
        ok = precinto not in ("NO DETECTADO", "NO_DETECTADA", None)
        return {"ocr_raw": texto, "precinto": precinto if ok else None, "valido": ok}

    def verificar_contenedor(self, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Extrae y valida un código ISO 6346 desde el OCR.
        Retorna: {"ocr_raw": str, "contenedor": str|None, "valido": bool}
        """
        texto = self._ocr(imagen_bytes)
        code = rules.extraer_contenedor(texto)
        ok = bool(code) and code != "NO DETECTADO" and rules.validar_iso6346(code)
        return {"ocr_raw": texto, "contenedor": code if ok else None, "valido": ok}

    # ==========================================================================
    #   Entrada universal desde el endpoint
    # ==========================================================================

    def verify_with_question(self, question_id, image_file) -> Dict[str, Any]:
        """
        Flujo completo: consulta la pregunta, prepara la imagen y enruta la verificación.

        Returns:
            Dict con `ocr_raw`, campo derivado (placa/precinto/contenedor) si aplica,
            `valido` y `semantic_tag` encontrado.

        Raises:
            ValueError: si no se suministró `question_repo` al inicializar.
            EntityNotFoundError: si la pregunta no existe.
            InvalidImageError: si la imagen es inválida o vacía.
            ExtractionError: si el OCR subyacente falla.
        """
        if not self.question_repo:
            raise ValueError("Question repository must be provided during service initialization")

        question = self.question_repo.get(question_id)
        if not question:
            raise EntityNotFoundError(
                message=f"Pregunta con id {question_id} no encontrada",
                entity_type="Question",
                entity_id=str(question_id),
            )

        # Preparar datos de imagen y enrutar por semantic_tag
        imagen_bytes = self._prepare_image_data(image_file)
        tag = getattr(question, "semantic_tag", "") or "none"
        result = self.verificar_universal(tag, imagen_bytes)
        result["semantic_tag"] = tag
        return result

    def verificar_universal(self, tag: str, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Selecciona la regla correcta según `semantic_tag` (normalizado).
        Retorna dict con `ocr_raw`, campos derivados (placa/precinto/contenedor) y `valido`.
        """
        canon = rules.canonical_semantic_tag(tag)

        if canon == "placa":
            return self.verificar_placa(imagen_bytes)
        if canon == "precinto":
            return self.verificar_precinto(imagen_bytes)
        if canon == "contenedor":
            return self.verificar_contenedor(imagen_bytes)

        # Fallback genérico: sólo texto y si hay algo no vacío.
        texto = self._ocr(imagen_bytes)
        return {"ocr_raw": texto, "valido": bool(texto.strip())}

    # ==========================================================================
    #   Internos
    # ==========================================================================

    def _prepare_image_data(self, image_file):
        """
        Prepara el objeto de archivo para lectura y devuelve bytes.

        Comportamiento:
        - Si el objeto tiene `seek`, se posiciona al inicio.
        - Si `read()` entrega vacío, se considera imagen inválida.

        Raises:
            InvalidImageError: sin archivo o vacío.
        """
        if not image_file:
            raise InvalidImageError(message="No se proporcionó ninguna imagen", image_format="none")

        try:
            if hasattr(image_file, "seek"):
                image_file.seek(0)
        except Exception:
            # En caso de que `seek` falle: continuar y depender de `read()`
            pass

        imagen_bytes = image_file.read()
        if not imagen_bytes:
            raise InvalidImageError(message="Imagen vacía", image_size=0)

        return imagen_bytes

    def _ocr(self, imagen_bytes: bytes) -> str:
        """
        Realiza OCR usando el puerto `TextExtractorPort`.

        Returns:
            Texto plano extraído (strip aplicado).

        Raises:
            InvalidImageError: si bytes están vacíos.
            ExtractionError: si la implementación del extractor falla.
        """
        if not imagen_bytes:
            raise InvalidImageError(message="Imagen vacía.", image_size=0)
        try:
            texto = self.text_extractor.extract_text(imagen_bytes) or ""
        except Exception as e:
            raise ExtractionError(
                message=f"OCR falló: {e}",
                service_name="text_extractor",
                error_code=type(e).__name__,
            ) from e
        return texto.strip()
