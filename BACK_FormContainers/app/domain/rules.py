# -*- coding: utf-8 -*-
"""
Reglas de negocio y utilidades de normalización/validación relacionadas con OCR.

Incluye heurísticas para:
- Placas (CO):   ABC123
- Precintos:     mejor candidato alfanumérico (prefiere terminar en dígito).
- Contenedores:  ISO 6346 (AAAA1234567) con validación completa.

Notas:
- Este módulo no depende de frameworks; puede usarse desde servicios y repositorios.
- Separamos helpers internos (prefijo `_`) de la API pública (expuesta en `__all__`).
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
import re
import unicodedata
from typing import Optional

# ── API pública ────────────────────────────────────────────────────────────────
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

# ==============================================================================
#   Normalización de semantic_tag (slugs usados en la BD)
# ==============================================================================

def _nfkc_upper(s: Optional[str]) -> str:
    """Normaliza a NFKC y mayúsculas; `None` se trata como cadena vacía."""
    return unicodedata.normalize("NFKC", (s or "")).upper()


def _slugify_tag(s: Optional[str]) -> str:
    """
    Slug simple para tags semánticos:
      - Quita acentos (NFKD → ASCII).
      - Sustituye espacios y separadores comunes por `-`.
      - Pasa a minúsculas.
    """
    txt = unicodedata.normalize("NFKD", (s or "").strip()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\s_/]+", "-", txt.strip().lower())


# Mapeo a slugs canónicos aceptados en la base de datos
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
    Devuelve el slug canónico para `semantic_tag`, compatible con la migración:
    {'none','placa','proveedor','transportista','receptor','contenedor','precinto'}.
    """
    s = _slugify_tag(raw)
    return _CANON_MAP.get(s, "none")


def is_actor_tag(tag: Optional[str]) -> bool:
    """True si el tag canónico corresponde a entidades de actor (proveedor/transportista/receptor)."""
    return canonical_semantic_tag(tag) in {"proveedor", "transportista", "receptor"}


# ==============================================================================
#   Utilidades internas para OCR (NO cambian contratos públicos)
# ==============================================================================

_MESES_LARGO = {
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
}
_MESES_CORTO = {"ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"}
_HORA_MARKERS = ("A.M", "AM", "P.M", "PM", "A. M", "P. M")


def _line_seems_camera_stamp(line: str) -> bool:
    """
    Heurística liviana: detecta líneas tipo '23 de mayo de 2025 7:18 a. m.'
    o '21/07/2025 07:15 AM' para poder descartarlas del OCR.
    """
    L = _nfkc_upper((line or "").strip())
    if not L:
        return False
    # dd/mm/yyyy o yyyy-mm-dd (+ hora opcional)
    if re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", L):
        if ":" in L or any(h in L for h in _HORA_MARKERS):
            return True
    # “23 de MAYO de 2025 7:18 A. M.”
    if any(m in L for m in (_MESES_LARGO | _MESES_CORTO)) and re.search(r"\b20\d{2}\b", L):
        return True
    # hh:mm con marcador AM/PM
    if re.search(r"\b\d{1,2}:\d{2}\b", L) and any(h in L for h in _HORA_MARKERS):
        return True
    return False


def _strip_camera_stamps(texto: str) -> str:
    """Quita las líneas que parecen la marca de fecha/hora de la cámara."""
    kept = []
    for ln in (texto or "").splitlines():
        if not _line_seems_camera_stamp(ln):
            kept.append(ln)
    return "\n".join(kept)


def _is_probable_date_number(num: str) -> bool:
    """Filtro extra para fallback numérico: evita YYYYMMDD / DDMMYYYY / HHMMSS."""
    n = num.strip()
    if not re.fullmatch(r"\d{6,8}", n):
        return False
    # YYYYMMDD
    if re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", n):
        return True
    # DDMMYYYY
    if re.fullmatch(r"(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])20\d{2}", n):
        return True
    # HHMMSS (muy laxo, pero evita falsos típicos)
    if re.fullmatch(r"([01]\d|2[0-3])[0-5]\d[0-5]\d", n):
        return True
    return False


# Detecta y elimina duplicación exacta (ABCD...ABCD... -> ABCD...)
_DUP_RE = re.compile(r"^(.{5,})\1+$")


def _undouble(token: str) -> str:
    """Reduce duplicación exacta en el token (p. ej., 'EBS0053049EBS0053049' → 'EBS0053049')."""
    t = token or ""
    m = _DUP_RE.match(t)
    if m:
        return m.group(1)
    # caso simple: mitad=mitad
    n = len(t)
    if n % 2 == 0 and n >= 10 and t[: n // 2] == t[n // 2 :]:
        return t[: n // 2]
    return t


# NIT colombiano (con o sin puntos) opcionalmente precedido por la palabra NIT
_NIT_WORD_RE = re.compile(r"\bN\.?\s*I\.?\s*T\.?\b[:\s-]*", re.IGNORECASE)
_NIT_NUM_RE = re.compile(r"\b\d{3}(?:[.\s]?\d{3}){2}-?\d\b")  # 900.632.994-2 | 900632994-2


def _strip_nit(texto: str) -> str:
    """
    Quita segmentos 'NIT ....' completos para que no entren al ranking
    y también la forma numérica típica si aparece sola.
    """
    T = texto
    # 1) eliminar 'NIT: 900.632.994-2' (con variaciones)
    T = re.sub(_NIT_WORD_RE.pattern + r"(?:\d{3}(?:[.\s]?\d{3}){2}-?\d)", " ", T, flags=re.IGNORECASE)
    # 2) eliminar números con formato típico de NIT
    T = _NIT_NUM_RE.sub(" ", T)
    return T


# ==============================================================================
#   Reglas de OCR
# ==============================================================================

# =============== Placas (CO) ===============

_PLACA_RE = re.compile(r"([A-Z]{3})(\d{3})")  # Referencia: formato ABC123 (se usa en validaciones internas)


def normalizar_placa(texto: Optional[str]) -> str:
    """
    Detecta una placa colombiana (3 letras + 3 dígitos) en formatos:
    'ABC123', 'ABC-123', 'abc 123', 'A B C 1 2 3'.

    Devuelve:
        - 'ABC123' si hay match.
        - 'NO_DETECTADA' en caso contrario.

    Notas:
        - Se ignoran falsos positivos derivados de timestamps de cámara,
          por ejemplo 'MAY708', 'JUN715', etc.
    """
    if not texto:
        return "NO_DETECTADA"

    # 1) Eliminar líneas de timestamp de cámara
    t = _strip_camera_stamps(texto)

    # 2) Buscar candidatos y descartar meses (MAY, JUN, JUL...) como prefijo
    def _pick(s: str) -> str:
        for m in re.finditer(r"[A-Z]{3}\d{3}", s):
            pref = m.group(0)[:3]
            if pref in _MESES_CORTO:  # evita 'MAY708'/'JUN701'...
                continue
            return m.group(0)
        return ""

    compact = re.sub(r"[^A-Za-z0-9]", "", _nfkc_upper(t))
    got = _pick(compact)
    if got:
        return got

    # Fallback: solo quitar espacios (por si vienen 'A B C 1 2 3')
    loose = re.sub(r"\s+", "", _nfkc_upper(t))
    got = _pick(loose)
    if got:
        return got

    return "NO_DETECTADA"


# =============== Precintos ===============

def _is_container_like(s: str) -> bool:
    """Evita confundir un contenedor ISO 6346 (AAAA9999999) con un precinto."""
    return bool(re.fullmatch(r"[A-Z]{4}\d{7}", s))


def _score_precinto(c: str) -> int:
    """
    Scoring ajustado para priorizar el mejor precinto:

      +20 si longitud ideal 6–8
      +10 si 5 o 9
      -10 si >9 (p.ej., NIT) salvo que no haya otra opción
      +6 si mezcla letras y dígitos
      +5 si termina en dígito
      -8 si termina en letras (ruido '…ABC')
      -4 si muchos ceros al inicio
      -2 por cada corrida >=4 del mismo carácter
    """
    L = len(c)
    s = 0
    if 6 <= L <= 8: s += 20
    elif L in (5, 9): s += 10
    elif L > 9: s -= 10
    if re.search(r"[A-Z]", c) and re.search(r"\d", c): s += 6
    if c[-1].isdigit(): s += 5
    if re.search(r"\d+[A-Z]+$", c): s -= 8
    if re.match(r"0{3,}", c): s -= 4
    s -= 2 * len(re.findall(r"(.)\1{3,}", c))
    return s


def limpiar_precinto(texto: Optional[str]) -> str:
    """
    Extrae un precinto alfanumérico robusto desde texto OCR:

    - Une tokens contiguos (A123 + 45 -> A12345).
    - Evita duplicados exactos (X...X...).
    - Evita NIT.
    - Prefiere longitudes 6–8 y que termine en dígito.
    - Fallback: numérico largo (excluyendo fechas HHMMSS / YYYYMMDD / DDMMYYYY).

    Retorna:
        - Mejor candidato por score.
        - 'NO DETECTADO' si no hay suficientes evidencias.
    """
    if not texto:
        return "NO DETECTADO"

    # 1) Normalizar y quitar timestamp + NIT
    t = _nfkc_upper(_strip_nit(_strip_camera_stamps(texto)))

    candidates = set()

    # 2) Bloques contiguos
    for m in re.finditer(r"[A-Z0-9]{5,}", t):
        candidates.add(m.group(0))

    # 3) Colapsar separadores A..Z0-9 + sep + A..Z0-9
    for sp in re.findall(r"(?:[A-Z0-9]{2,}[^A-Z0-9]+){1,}[A-Z0-9]{2,}", t):
        join = re.sub(r"[^A-Z0-9]+", "", sp)
        candidates.add(_undouble(join))  # reducir duplicación si quedó pegado

    # 4) Ventanas: token con letras seguido de grupos numéricos cortos
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
            candidates.add(_undouble(acc))

    # 5) Limpieza + filtros
    cleaned = []
    for c in candidates:
        c0 = re.sub(r"[^A-Z0-9]", "", c)
        if len(c0) < 5:
            continue
        # eliminar duplicación exacta (EBS0053049EBS0053049)
        c0 = _undouble(c0)
        # evitar ISO6346 (AAAA#######)
        if re.fullmatch(r"[A-Z]{4}\d{7}", c0):
            continue
        # evitar patrones de fecha/horario como fallback
        digits = re.sub(r"\D", "", c0)
        if 6 <= len(digits) <= 8 and (
            re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", digits) or   # YYYYMMDD
            re.fullmatch(r"(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])20\d{2}", digits) or   # DDMMYYYY
            re.fullmatch(r"([01]\d|2[0-3])[0-5]\d[0-5]\d", digits)                    # HHMMSS
        ):
            continue
        cleaned.append(c0)

    if not cleaned:
        # 6) Fallback: numérico 5–9 más plausible (evitar fechas)
        nums = []
        for m in re.finditer(r"\b(?<!\d)(\d{5,9})(?!\d)\b", t):
            d = m.group(1)
            if not (
                re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", d) or
                re.fullmatch(r"(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])20\d{2}", d) or
                re.fullmatch(r"([01]\d|2[0-3])[0-5]\d[0-5]\d", d)
            ):
                nums.append(d)
        return max(nums, key=lambda x: (6 <= len(x) <= 8, len(x)), default="NO DETECTADO")

    # 7) Si hay candidatos de longitud típica 6–8, priorizarlos
    typical = [c for c in cleaned if 6 <= len(c) <= 8]
    pool = typical or cleaned
    if typical:
        # descartar numéricos >=9 (p.ej., NIT enmascarados)
        pool = [c for c in pool if not re.fullmatch(r"9\d{8,9}", re.sub(r"\D", "", c))]

    # 8) Elegir el mejor por score
    best = max(pool, key=_score_precinto)
    return best or "NO DETECTADO"


# =============== Contenedores ISO 6346 ===============

_ISO_CANDIDATE_RE = re.compile(r"[A-Z]{4}\d{7}")


def extraer_contenedor(texto: Optional[str]) -> str:
    """
    Busca códigos ISO 6346 en el texto y retorna el primero que pase validación.

    Retorna:
        - Código ISO válido ('AAAA1234567').
        - 'NO DETECTADO' si no hay ninguno válido.
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
    Valida un código ISO 6346 con tabla oficial de valores y pesos `2**i`.

    Formato:
        'AAAA1234567' → 4 letras (propietario/tipo) + 7 dígitos (incluye dígito de control).

    Regla:
        - Se calcula el dígito de control como `((sum(valor_i * 2**i)) % 11) % 10`
          sobre los 10 primeros caracteres.
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
