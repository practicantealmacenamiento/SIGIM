"""
Detector de precintos simplificado y optimizado para los casos reales.
Basado en los patrones observados en las imágenes del usuario.
"""

import re
import unicodedata
from typing import Optional, Dict, List

def detect_precinto_simple(texto: Optional[str]) -> str:
    """
    Detector simplificado de precintos basado en patrones reales.
    
    Patrones soportados:
    - Números de 6-8 dígitos: 0048604
    - Letras + números: WK01305
    - Con separadores: WK 01305, WK-01305
    - Con ruido: PRECINTO 0048604, SELLO WK01305
    """
    if not texto:
        return "NO DETECTADO"
    
    # Normalizar texto
    texto = unicodedata.normalize("NFKC", texto).upper().strip()
    
    # Remover ruido común
    texto = re.sub(r'\b(PRECINTO|SELLO|SEAL|SECURITY|SEGURIDAD|NUMERO|NUMBER|NUM|NO\.?|DE|OF|DEL|THE)\b', ' ', texto)
    texto = re.sub(r'[^\w\s]', ' ', texto)  # Remover símbolos
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # Patrón 1: Solo números de 6-8 dígitos (0048604)
    match = re.search(r'\b\d{6,8}\b', texto)
    if match:
        numero = match.group()
        # Evitar fechas y otros patrones no deseados
        if not re.match(r'^(19|20)\d{6}$', numero):  # No fechas tipo 20240101
            return numero
    
    # Patrón 2: Letras seguidas de números (WK01305)
    match = re.search(r'\b[A-Z]{2,4}\s*\d{4,8}\b', texto)
    if match:
        precinto = re.sub(r'\s+', '', match.group())
        return precinto
    
    # Patrón 3: Números seguidos de letras (menos común)
    match = re.search(r'\b\d{3,6}[A-Z]{2,4}\b', texto)
    if match:
        return match.group()
    
    # Patrón 4: Combinaciones mixtas más complejas
    match = re.search(r'\b[A-Z0-9]{6,12}\b', texto)
    if match:
        candidato = match.group()
        # Debe tener al menos un número
        if re.search(r'\d', candidato):
            # No debe ser placa colombiana (ABC123)
            if not re.match(r'^[A-Z]{3}\d{3}$', candidato):
                # No debe ser contenedor ISO (AAAA1234567)
                if not re.match(r'^[A-Z]{4}\d{7}$', candidato):
                    return candidato
    
    return "NO DETECTADO"


def get_precinto_info_simple(texto: Optional[str]) -> Dict:
    """
    Versión simplificada que retorna información de detección.
    """
    if not texto:
        return {
            "precinto": "NO DETECTADO",
            "confianza": 0.0,
            "razon": "texto_vacio",
            "texto_limpio": "",
            "candidatos": []
        }
    
    # Limpiar texto para análisis
    texto_limpio = unicodedata.normalize("NFKC", texto).upper().strip()
    
    # Extraer todos los candidatos posibles para debugging
    candidatos = []
    
    # Buscar patrones de números de 6-8 dígitos
    numeros = re.findall(r'\b\d{6,8}\b', texto_limpio)
    for num in numeros:
        if not re.match(r'^(19|20)\d{6}$', num):  # No fechas
            candidatos.append({"valor": num, "tipo": "numerico", "confianza": 0.9})
    
    # Buscar patrones de letras + números
    alfanumericos = re.findall(r'\b[A-Z]{2,4}\s*\d{4,8}\b', texto_limpio)
    for match in alfanumericos:
        clean_match = re.sub(r'\s+', '', match)
        candidatos.append({"valor": clean_match, "tipo": "alfanumerico", "confianza": 0.95})
    
    # Buscar otros patrones mixtos
    mixtos = re.findall(r'\b[A-Z0-9]{6,12}\b', texto_limpio)
    for match in mixtos:
        if re.search(r'\d', match) and not re.match(r'^[A-Z]{3}\d{3}$', match) and not re.match(r'^[A-Z]{4}\d{7}$', match):
            candidatos.append({"valor": match, "tipo": "mixto", "confianza": 0.8})
    
    precinto = detect_precinto_simple(texto)
    
    if precinto == "NO DETECTADO":
        return {
            "precinto": "NO DETECTADO",
            "confianza": 0.0,
            "razon": "sin_patron_valido",
            "texto_limpio": texto_limpio,
            "candidatos": candidatos
        }
    
    # Calcular confianza básica
    confianza = 0.8  # Base
    
    # Bonificaciones
    if re.match(r'^\d{6,8}$', precinto):  # Solo números largos
        confianza = 0.9
    elif re.match(r'^[A-Z]{2,4}\d{4,8}$', precinto):  # Formato típico
        confianza = 0.95
    
    return {
        "precinto": precinto,
        "confianza": confianza,
        "razon": "detectado",
        "texto_limpio": texto_limpio,
        "candidatos": candidatos
    }


# Función de compatibilidad
def limpiar_precinto_simple(texto: Optional[str]) -> str:
    """Función compatible con el sistema existente."""
    return detect_precinto_simple(texto)
