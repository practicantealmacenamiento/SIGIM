"""Reglas especializadas para la detección de precintos de seguridad.

Este módulo encapsula la lógica de puntuación y ranking de candidatos que
provienen de texto OCR ruidoso. Sigue los principios de Clean Architecture:

* No depende de Django ni del ORM.
* Expone entidades inmutables que pueden ser usadas por servicios en la capa
  de aplicación.
* Ofrece funciones utilitarias para integrarse con comandos y vistas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.domain import rules

__all__ = [
    "PrecintoCandidate",
    "PrecintoDetector",
    "limpiar_precinto_mejorado",
    "get_precinto_detection_info",
]


PRECINTO_CONFIDENCE_THRESHOLD = 0.7


@dataclass(frozen=True)
class PrecintoCandidate:
    """Representa un candidato a precinto detectado en un texto OCR."""

    texto: str
    confianza: float
    razones: Sequence[str]

    @property
    def text(self) -> str:
        return self.texto

    @property
    def confidence(self) -> float:
        return self.confianza

    def to_dict(self) -> dict:
        return {
            "texto": self.texto,
            "confianza": self.confianza,
            "razones": list(self.razones),
        }


class PrecintoDetector:
    """Detector de precintos basado en heurísticas robustas."""

    def __init__(self, *, umbral_confianza: float = PRECINTO_CONFIDENCE_THRESHOLD):
        self.umbral_confianza = umbral_confianza

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def detect_precintos(self, texto: Optional[str]) -> List[PrecintoCandidate]:
        """
        Retorna candidatos ordenados por confianza.

        El detector es tolerante a ruido, separadores y combinaciones parciales.
        Filtra patrones que suelen ser falsos positivos (placas, contenedores).
        """

        texto_normalizado = _normalizar_texto(texto)
        if not texto_normalizado:
            return []

        candidatos_crudos = _generar_candidatos(texto_normalizado)
        candidatos = []

        for cand in candidatos_crudos:
            evaluacion = _evaluar_candidato(cand, texto_normalizado)
            if evaluacion is None:
                continue
            candidatos.append(evaluacion)

        candidatos.sort(key=lambda c: (c.confianza, len(c.texto)), reverse=True)
        return candidatos


# ----------------------------------------------------------------------
# Funciones de alto nivel usadas por comandos/tests
# ----------------------------------------------------------------------
def limpiar_precinto_mejorado(texto: Optional[str]) -> str:
    """Devuelve el mejor precinto detectado o 'NO DETECTADO'."""

    detector = PrecintoDetector()
    candidatos = detector.detect_precintos(texto)
    contexto = _normalizar_texto(texto)
    if not candidatos:
        return _fallback_precinto(texto, contexto)

    mejor = candidatos[0]
    if mejor.confianza >= detector.umbral_confianza and _es_precinto_valido(mejor.texto):
        return mejor.texto

    fallback = _fallback_precinto(texto, contexto)
    return fallback


def get_precinto_detection_info(texto: Optional[str]) -> dict:
    """Retorna un diccionario con el diagnóstico completo de la detección."""

    detector = PrecintoDetector()
    candidatos = detector.detect_precintos(texto)
    contexto = _normalizar_texto(texto)

    if texto is None or not str(texto).strip():
        return {
            "precinto": "NO DETECTADO",
            "confianza": 0.0,
            "razon": "texto_vacio",
            "candidatos": [c.to_dict() for c in candidatos],
        }

    if not candidatos:
        fallback = _fallback_precinto(texto, contexto)
        if fallback == "NO DETECTADO":
            return {
                "precinto": "NO DETECTADO",
                "confianza": 0.0,
                "razon": "sin_candidatos_validos",
                "candidatos": [],
            }
        return {
            "precinto": fallback,
            "confianza": 0.75,
            "razon": "detectado",
            "candidatos": [],
        }

    mejor = candidatos[0]
    if mejor.confianza >= detector.umbral_confianza:
        razon = "detectado"
    elif mejor.confianza > 0:
        razon = "confianza_baja"
    else:
        razon = "sin_candidatos_validos"

    return {
        "precinto": mejor.texto if razon == "detectado" else "NO DETECTADO",
        "confianza": mejor.confianza if razon == "detectado" else 0.0,
        "razon": razon,
        "candidatos": [c.to_dict() for c in candidatos],
    }


# ----------------------------------------------------------------------
# Utilidades internas (dominio puro)
# ----------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[A-Z0-9]+")
_BLOQUE_RE = re.compile(r"[A-Z0-9]{5,}")
_PLACA_RE = re.compile(r"^[A-Z]{3}\d{3}$")
_CONTENEDOR_RE = re.compile(r"^[A-Z]{4}\d{7}$")
_REPETICION_RE = re.compile(r"(.)\1{3,}")


def _normalizar_texto(texto: Optional[str]) -> str:
    if texto is None:
        return ""
    compacto = unicodedata.normalize("NFKC", str(texto))
    return compacto.upper()


def _generar_candidatos(texto_normalizado: str) -> List[str]:
    candidatos: set[str] = set()

    for match in _BLOQUE_RE.finditer(texto_normalizado):
        candidatos.add(match.group(0))

    tokens = _TOKEN_RE.findall(texto_normalizado)
    for token in tokens:
        if len(token) >= 5:
            candidatos.add(token)

    for i, token in enumerate(tokens):
        if not re.search(r"[A-Z]", token):
            continue
        combinado = token
        for siguiente in tokens[i + 1 : i + 4]:
            if re.fullmatch(r"\d{1,4}", siguiente):
                combinado += siguiente
                if len(combinado) >= 5:
                    candidatos.add(combinado)
            else:
                break

    compacto = re.sub(r"[^A-Z0-9]", "", texto_normalizado)
    if len(compacto) >= 5:
        candidatos.add(compacto)

    resultado: set[str] = set()
    for cand in candidatos:
        base = re.sub(r"[^A-Z0-9]", "", cand)
        if len(base) < 5 or not re.search(r"\d", base):
            continue
        resultado.add(base)
        if not base[-1].isdigit():
            trimmed = re.sub(r"[A-Z]+$", "", base)
            if len(trimmed) >= 5 and re.search(r"\d", trimmed):
                resultado.add(trimmed)

    return list(resultado)[:50]


def _evaluar_candidato(texto: str, contexto: str) -> Optional[PrecintoCandidate]:
    base = re.sub(r"[^A-Z0-9]", "", texto)
    if len(base) < 5:
        return None

    if _CONTENEDOR_RE.match(base):
        return None
    if _PLACA_RE.match(base) and "PLACA" in contexto:
        return None

    razones: list[str] = []
    confianza = 0.5

    if re.search(r"[A-Z]", base) and re.search(r"\d", base):
        confianza += 0.25
        razones.append("alfanumerico")
    else:
        confianza -= 0.25
        razones.append("caracteres_insuficientes")

    if base[-1].isdigit():
        confianza += 0.1
        razones.append("termina_en_digito")
    if 6 <= len(base) <= 8:
        confianza += 0.1
        razones.append("longitud_optima")
    elif len(base) > 10:
        confianza -= 0.1
        razones.append("longitud_larga")

    if _REPETICION_RE.search(base):
        confianza -= 0.1
        razones.append("repeticiones_largas")

    # Penalizar si parece un identificador puramente numérico
    if base.isdigit():
        confianza = min(confianza, 0.45)
        razones.append("solo_numeros")

    confianza = max(0.0, min(round(confianza, 2), 0.99))

    return PrecintoCandidate(texto=base, confianza=confianza, razones=tuple(razones))


def _es_precinto_valido(codigo: Optional[str]) -> bool:
    if not codigo:
        return False
    if len(codigo) < 5:
        return False
    if not re.search(r"[A-Z]", codigo):
        return False
    if not re.search(r"\d", codigo):
        return False
    if "PLACA" in codigo or "CONTENEDOR" in codigo:
        return False
    if _CONTENEDOR_RE.match(codigo):
        return False
    return True


def _fallback_precinto(texto: Optional[str], contexto: Optional[str]) -> str:
    resultado_legacy = rules.limpiar_precinto(texto)
    contexto = contexto or _normalizar_texto(texto)
    if contexto and "PLACA" in contexto and _PLACA_RE.match(resultado_legacy or ""):
        return "NO DETECTADO"
    if _es_precinto_valido(resultado_legacy):
        return resultado_legacy
    return "NO DETECTADO"

