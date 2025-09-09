"""
Reglas de negocio y utilidades de normalización/validación.
- Placas (CO):   ABC123
- Precintos:     mejor candidato alfanumérico (preferir que termine en dígito).
- Contenedores:  ISO 6346 (AAAA1234567) validado.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

__all__ = [
    # semántica
    "canonical_semantic_tag",
    "is_actor_tag",
    # reglas OCR / normalizaciones
    "normalizar_placa",
    "limpiar_precinto",
    "extraer_contenedor",
    "validar_iso6346",
]

# ---------------------------------------------------------------------
# Normalización de semantic_tag (slugs usados en la BD)
# ---------------------------------------------------------------------

def _nfkc_upper(s: Optional[str]) -> str:
    return unicodedata.normalize("NFKC", (s or "")).upper()

def _slugify_tag(s: Optional[str]) -> str:
    # simplificado: quitar acentos, bajar a ASCII básico
    txt = unicodedata.normalize("NFKD", (s or "").strip()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\s_/]+", "-", txt.strip().lower())

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
    Devuelve el slug canónico para el semantic_tag compatible con la migración:
    {'none','placa','proveedor','transportista','receptor','contenedor','precinto'}.
    """
    s = _slugify_tag(raw)
    return _CANON_MAP.get(s, "none")

def is_actor_tag(tag: Optional[str]) -> bool:
    return canonical_semantic_tag(tag) in {"proveedor", "transportista", "receptor"}

# ---------------------------------------------------------------------
# Reglas de OCR (tus reglas originales, intactas y acopladas)
# ---------------------------------------------------------------------

# =============== Placas (CO) ===============
_PLACA_RE = re.compile(r"([A-Z]{3})(\d{3})")

def normalizar_placa(texto: Optional[str]) -> str:
    """
    Detecta una placa colombiana (3 letras + 3 dígitos) en formatos:
    'ABC123', 'ABC-123', 'abc 123', 'A B C 1 2 3'.
    Devuelve 'ABC123' o 'NO_DETECTADA' si no hay match.
    """
    if not texto:
        return "NO_DETECTADA"
    compact = re.sub(r"[^A-Za-z0-9]", "", texto).upper()
    m = _PLACA_RE.search(compact)
    if not m:
        loose = re.sub(r"\s+", "", texto.upper())
        m = _PLACA_RE.search(loose)
    if m:
        letras, numeros = m.groups()
        return f"{letras}{numeros}"
    return "NO_DETECTADA"

# =============== Precintos ===============

def _is_container_like(s: str) -> bool:
    # Evita confundir un contenedor ISO 6346 (AAAA9999999) con un precinto
    return bool(re.fullmatch(r"[A-Z]{4}\d{7}", s))

def _score_precinto(c: str) -> int:
    # Prefiere mixtos y sobre todo que TERMINEN en dígito
    s = len(c)
    if re.search(r"[A-Z]", c) and re.search(r"\d", c):
        s += 4
    if re.search(r"\d$", c):
        s += 12
    if re.search(r"\d+[A-Z]+$", c):
        s -= 6
    runs = re.findall(r"(.)\1{3,}", c)
    s -= 2 * len(runs)
    return s

def limpiar_precinto(texto: Optional[str]) -> str:
    """
    Extrae un precinto alfanumérico robusto:
    - Une tokens contiguos (p.ej. 'TDM388' + '16' → 'TDM38816').
    - Colapsa separadores arbitrarios.
    - Recorta sufijos alfabéticos tras el último dígito.
    - Prefiere candidatos que TERMINEN en dígito.
    - Evita ISO6346 si hay alternativas.
    - Fallback: secuencia numérica más larga.
    """
    if not texto:
        return "NO DETECTADO"

    t = _nfkc_upper(texto)
    candidates = set()

    # 1) Bloques contiguos alfanuméricos
    candidates.update(re.findall(r"[A-Z0-9]{5,}", t))

    # 2) Colapsar separadores
    for sp in re.findall(r"(?:[A-Z0-9]{2,}[^A-Z0-9]+){1,}[A-Z0-9]{2,}", t):
        candidates.add(re.sub(r"[^A-Z0-9]+", "", sp))

    # 3) Ventanas: ancla con letras + tokens numéricos cortos siguientes
    tokens = re.findall(r"[A-Z0-9]+", t)
    for i, tok in enumerate(tokens):
        if not re.search(r"[A-Z]", tok):
            continue
        acc = tok
        j = i + 1
        while j < len(tokens) and re.fullmatch(r"\d{1,4}", tokens[j]):
            acc += tokens[j]
            j += 1
        if len(acc) >= 5:
            candidates.add(acc)

    if not candidates:
        nums = re.findall(r"\d+", t)
        return max(nums, key=len) if nums else "NO DETECTADO"

    # 4) Variante recortada de sufijo alfabético
    trimmed = set()
    for c in candidates:
        c2 = re.sub(r"(\d)[A-Z]+$", r"\1", c)
        if len(c2) >= 5:
            trimmed.add(c2)
    candidates |= trimmed

    # 5) Filtrado básico
    filtered = [c for c in candidates if 5 <= len(c) <= 24 and re.search(r"\d", c)]
    if not filtered:
        nums = re.findall(r"\d+", t)
        return max(nums, key=len) if nums else "NO DETECTADO"

    # 6) Evitar ISO6346 si hay alternativas
    pool = [c for c in filtered if not _is_container_like(c)] or filtered

    # 7) Elegir mejor
    best = max(pool, key=_score_precinto)
    return best or "NO DETECTADO"

# =============== Contenedores ISO 6346 ===============
_ISO_CANDIDATE_RE = re.compile(r"[A-Z]{4}\d{7}")

def extraer_contenedor(texto: Optional[str]) -> str:
    """
    Busca códigos ISO 6346. Devuelve el primero que pase validación.
    Si ninguno es válido → 'NO DETECTADO'.
    """
    if not texto:
        return "NO DETECTADO"
    compact = re.sub(r"[^A-Za-z0-9]", "", _nfkc_upper(texto))
    for m in _ISO_CANDIDATE_RE.finditer(compact):
        code = m.group(0)
        if validar_iso6346(code):
            return code
    return "NO DETECTADO"

def validar_iso6346(code: str) -> bool:
    """
    Valida ISO 6346 con tabla oficial y pesos 2**i.
    Formato: 'AAAA1234567' (4 letras + 7 dígitos). Último es dígito de control.
    """
    if not isinstance(code, str):
        return False
    code = code.upper()
    if not re.fullmatch(r"[A-Z]{4}\d{7}", code):
        return False

    # Valores letra (ISO 6346) — notar saltos L=23, V=34
    valores_letras = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18,
        'I': 19, 'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27,
        'Q': 28, 'R': 29, 'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35, 'X': 36,
        'Y': 37, 'Z': 38
    }
    prefijo = code[:4]
    numeros = code[4:]

    try:
        digitos = [valores_letras[ch] for ch in prefijo] + [int(d) for d in numeros[:-1]]
    except KeyError:
        return False

    pesos = [2 ** i for i in range(len(digitos))]
    total = sum(v * p for v, p in zip(digitos, pesos))
    digito_control = (total % 11) % 10
    return digito_control == int(numeros[-1])
