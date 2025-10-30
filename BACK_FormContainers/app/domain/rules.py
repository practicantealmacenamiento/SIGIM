# -*- coding: utf-8 -*-
"""
Reglas de normalización y heurísticas auxiliares para el dominio.

El módulo reúne utilidades orientadas a:
    - Etiquetas semánticas (`canonical_semantic_tag`, `is_actor_tag`).
    - Detección y limpieza de placas colombianas.
    - Identificación de precintos con criterios heurísticos.
    - Extracción y validación de códigos ISO 6346.

Todas las funciones son agnósticas de infraestructura y pueden emplearse
tanto en servicios de aplicación como en repositorios.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

__all__ = [
    # etiquetas
    "canonical_semantic_tag",
    "is_actor_tag",
    # OCR / normalizaciones
    "normalizar_placa",
    "limpiar_precinto",
    "extraer_contenedor",
    "validar_iso6346",
]

# ---------------------------------------------------------------------------
# Etiquetas semánticas
# ---------------------------------------------------------------------------

_CANON_MAP = {
    "none": "none",
    "placa": "placa",
    "placa-vehicular": "placa",
    "matricula": "placa",
    "contenedor": "contenedor",
    "contenedor-iso": "contenedor",
    "container": "contenedor",
    "iso6346": "contenedor",
    "precinto": "precinto",
    "sello": "precinto",
    "precinto-de-seguridad": "precinto",
    "proveedor": "proveedor",
    "transportista": "transportista",
    "receptor": "receptor",
    "usuario-que-recibe": "receptor",
    "receiver": "receptor",
}


def canonical_semantic_tag(raw: Optional[str]) -> str:
    """
    Convierte una etiqueta libre en el slug canónico admitido por el dominio.
    """
    slug = _slugify_tag(raw)
    return _CANON_MAP.get(slug, "none")


def is_actor_tag(tag: Optional[str]) -> bool:
    """
    Indica si la etiqueta canónica pertenece al conjunto de actores (proveedor,
    transportista o receptor).
    """
    return canonical_semantic_tag(tag) in {"proveedor", "transportista", "receptor"}


# ---------------------------------------------------------------------------
# Utilidades internas de normalización
# ---------------------------------------------------------------------------

_MESES_LARGO = {
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
}

_MESES_CORTO = {
    "ENE",
    "FEB",
    "MAR",
    "ABR",
    "MAY",
    "JUN",
    "JUL",
    "AGO",
    "SEP",
    "OCT",
    "NOV",
    "DIC",
}

_HORA_MARKERS = ("A.M", "AM", "P.M", "PM", "A. M", "P. M")


def _nfkc_upper(value: Optional[str]) -> str:
    """
    Normaliza una cadena a NFKC en mayúsculas; `None` se interpreta como vacío.
    """
    return unicodedata.normalize("NFKC", (value or "")).upper()


def _slugify_tag(value: Optional[str]) -> str:
    """
    Convierte etiquetas sueltas en un slug ASCII minúsculo.
    """
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\s_/]+", "-", text.strip().lower())


def _line_seems_camera_stamp(line: str) -> bool:
    """
    Determina si una línea parece ser el sello de fecha/hora de la cámara.
    """
    upper = _nfkc_upper((line or "").strip())
    if not upper:
        return False

    # Formatos básicos con fecha y posible hora
    if re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", upper):
        if ":" in upper or any(marker in upper for marker in _HORA_MARKERS):
            return True

    if any(month in upper for month in (_MESES_LARGO | _MESES_CORTO)) and re.search(r"\b20\d{2}\b", upper):
        return True

    if re.search(r"\b\d{1,2}:\d{2}\b", upper) and any(marker in upper for marker in _HORA_MARKERS):
        return True

    return False


def _strip_camera_stamps(texto: str) -> str:
    """
    Elimina líneas que aparenten ser marcas de cámara (fecha/hora).
    """
    return "\n".join(
        line for line in (texto or "").splitlines() if not _line_seems_camera_stamp(line)
    )


def _strip_nit(texto: str) -> str:
    """
    Quita referencias directas a NIT para evitar falsos positivos al limpiar.
    """
    nit_word = re.compile(r"\bN\.?\s*I\.?\s*T\.?\b[:\s-]*", re.IGNORECASE)
    nit_number = re.compile(r"\b\d{3}(?:[.\s]?\d{3}){2}-?\d\b")

    cleaned = re.sub(
        nit_word.pattern + r"(?:\d{3}(?:[.\s]?\d{3}){2}-?\d)",
        " ",
        texto,
        flags=re.IGNORECASE,
    )
    return nit_number.sub(" ", cleaned)


def _is_probable_date_number(number: str) -> bool:
    """
    Detecta secuencias numéricas que podrían ser fechas u horas para descartarlas.
    """
    digits = number.strip()
    if not re.fullmatch(r"\d{6,8}", digits):
        return False

    if re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", digits):
        return True
    if re.fullmatch(r"(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])20\d{2}", digits):
        return True
    if re.fullmatch(r"([01]\d|2[0-3])[0-5]\d[0-5]\d", digits):
        return True
    return False


_DUP_RE = re.compile(r"^(.{5,})\1+$")


def _undouble(token: str) -> str:
    """
    Reduce duplicaciones completas (ABCABC -> ABC) o simples (mitad repetida).
    """
    if not token:
        return ""
    match = _DUP_RE.match(token)
    if match:
        return match.group(1)
    length = len(token)
    if length % 2 == 0 and length >= 10 and token[: length // 2] == token[length // 2 :]:
        return token[: length // 2]
    return token


# ---------------------------------------------------------------------------
# Normalización de placas
# ---------------------------------------------------------------------------

_PLACA_RE = re.compile(r"([A-Z]{3})(\d{3})")


def normalizar_placa(texto: Optional[str]) -> str:
    """
    Busca y normaliza una placa colombiana en formato ABC123.
    Retorna la placa en mayúsculas o 'NO_DETECTADA' si no encuentra coincidencia.
    """
    if not texto:
        return "NO_DETECTADA"
    texto_normalizado = _nfkc_upper(texto)
    texto_normalizado = re.sub(r"[^A-Z0-9]", "", texto_normalizado)

    match = _PLACA_RE.search(texto_normalizado)
    if not match:
        return "NO_DETECTADA"
    letras, numeros = match.groups()
    return f"{letras}{numeros}"


# ---------------------------------------------------------------------------
# Limpieza de precintos
# ---------------------------------------------------------------------------

def _score_precinto(candidate: str) -> int:
    """
    Puntaje heurístico para priorizar el precinto más probable.
    """
    length = len(candidate)
    score = 0

    if 6 <= length <= 8:
        score += 20
    elif length in (5, 9):
        score += 10
    elif length > 9:
        score -= 10

    if re.search(r"[A-Z]", candidate) and re.search(r"\d", candidate):
        score += 6
    if candidate[-1].isdigit():
        score += 5
    if re.search(r"\d+[A-Z]+$", candidate):
        score -= 8
    if re.match(r"0{3,}", candidate):
        score -= 4
    score -= 2 * len(re.findall(r"(.)\1{3,}", candidate))
    return score


def limpiar_precinto(texto: Optional[str]) -> str:
    """
    Selecciona el precinto más plausible a partir de texto OCR.

    Estrategia:
        1. Normalización (mayúsculas, sin marcas de cámara ni NIT).
        2. Candidatos por bloques contiguos, colapso de separadores y ventanas.
        3. Filtrado de duplicados, fechas y patrones ISO.
        4. Selección por heurística de puntaje.

    Retorna el mejor candidato o 'NO DETECTADO'.
    """
    if not texto:
        return "NO DETECTADO"

    normalizado = _nfkc_upper(_strip_nit(_strip_camera_stamps(texto)))
    candidatos = set()

    for match in re.finditer(r"[A-Z0-9]{5,}", normalizado):
        candidatos.add(match.group(0))

    for fragmento in re.findall(r"(?:[A-Z0-9]{2,}[^A-Z0-9]+){1,}[A-Z0-9]{2,}", normalizado):
        juntos = re.sub(r"[^A-Z0-9]+", "", fragmento)
        candidatos.add(_undouble(juntos))

    tokens = re.findall(r"[A-Z0-9]+", normalizado)
    for index, token in enumerate(tokens):
        if not re.search(r"[A-Z]", token):
            continue
        acumulado = token
        siguiente = index + 1
        while siguiente < len(tokens) and re.fullmatch(r"\d{1,4}", tokens[siguiente]):
            acumulado += tokens[siguiente]
            siguiente += 1
        if len(acumulado) >= 5:
            candidatos.add(_undouble(acumulado))

    depurados = []
    for candidato in candidatos:
        limpio = re.sub(r"[^A-Z0-9]", "", candidato)
        if len(limpio) < 5:
            continue
        limpio = _undouble(limpio)
        if re.fullmatch(r"[A-Z]{4}\d{7}", limpio):
            continue
        digitos = re.sub(r"\D", "", limpio)
        if 6 <= len(digitos) <= 8 and _is_probable_date_number(digitos):
            continue
        depurados.append(limpio)

    if not depurados:
        numeros = []
        for match in re.finditer(r"\b(?<!\d)(\d{5,9})(?!\d)\b", normalizado):
            candidato = match.group(1)
            if not _is_probable_date_number(candidato):
                numeros.append(candidato)
        return max(numeros, key=lambda valor: (6 <= len(valor) <= 8, len(valor)), default="NO DETECTADO")

    preferidos = [c for c in depurados if 6 <= len(c) <= 8]
    universo = preferidos or depurados
    if preferidos:
        universo = [
            c for c in universo if not re.fullmatch(r"9\d{8,9}", re.sub(r"\D", "", c))
        ]

    return max(universo, key=_score_precinto) if universo else "NO DETECTADO"


# ---------------------------------------------------------------------------
# Contenedores ISO 6346
# ---------------------------------------------------------------------------

_ISO_CANDIDATE_RE = re.compile(r"[A-Z]{4}\d{7}")


def extraer_contenedor(texto: Optional[str]) -> str:
    """
    Busca el primer código ISO 6346 válido en el texto.
    """
    if not texto:
        return "NO DETECTADO"
    compacto = re.sub(r"[^A-Za-z0-9]", "", _nfkc_upper(texto))
    for match in _ISO_CANDIDATE_RE.finditer(compacto):
        codigo = match.group(0)
        if validar_iso6346(codigo):
            return codigo
    return "NO DETECTADO"


def validar_iso6346(code: str) -> bool:
    """
    Verifica el dígito de control de un código ISO 6346.
    """
    if not isinstance(code, str):
        return False
    code = code.upper()
    if not re.fullmatch(r"[A-Z]{4}\d{7}", code):
        return False

    valores = {
        "A": 10,
        "B": 12,
        "C": 13,
        "D": 14,
        "E": 15,
        "F": 16,
        "G": 17,
        "H": 18,
        "I": 19,
        "J": 20,
        "K": 21,
        "L": 23,
        "M": 24,
        "N": 25,
        "O": 26,
        "P": 27,
        "Q": 28,
        "R": 29,
        "S": 30,
        "T": 31,
        "U": 32,
        "V": 34,
        "W": 35,
        "X": 36,
        "Y": 37,
        "Z": 38,
    }

    prefijo = code[:4]
    numeros = code[4:]
    try:
        digitos = [valores[letra] for letra in prefijo] + [int(d) for d in numeros[:-1]]
    except KeyError:
        return False

    pesos = [2 ** i for i in range(len(digitos))]
    total = sum(valor * peso for valor, peso in zip(digitos, pesos))
    digito_control = (total % 11) % 10
    return digito_control == int(numeros[-1])
