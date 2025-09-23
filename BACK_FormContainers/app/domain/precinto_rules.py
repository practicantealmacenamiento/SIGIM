"""
Reglas mejoradas y más estrictas para detección de precintos.
Enfocado en detectar SOLO el texto del precinto, evitando ruido.
"""

import re
import unicodedata
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

__all__ = [
    "PrecintoDetector",
    "PrecintoCandidate", 
    "limpiar_precinto_mejorado"
]


@dataclass
class PrecintoCandidate:
    """Candidato a precinto con metadatos de confianza."""
    text: str
    confidence: float
    position: Tuple[int, int]  # (start, end) en texto original
    reasons: List[str]  # Razones por las que es buen candidato
    
    
class PrecintoDetector:
    """
    Detector mejorado de precintos con reglas más estrictas.
    Enfocado en precisión sobre recall.
    """
    
    # Patrones que NO son precintos (blacklist)
    BLACKLIST_PATTERNS = [
        r'^[A-Z]{3}\d{3}$',  # Placas colombianas (ABC123)
        r'^[A-Z]{4}\d{7}$',  # Contenedores ISO (AAAA1234567)
        r'^\d{4}[-/]\d{2}[-/]\d{2}$',  # Fechas
        r'^(PLACA|PLATE|CONTAINER|CONTENEDOR|FECHA|DATE)$',  # Palabras clave
        r'^\d{1,3}$',  # Números muy cortos
        r'^[A-Z]{1,2}$',  # Letras muy cortas
    ]
    
    # Patrones de ruido común en OCR
    NOISE_PATTERNS = [
        r'\b(PRECINTO|SELLO|SEAL|SECURITY|SEGURIDAD)\b',
        r'\b(NUMERO|NUMBER|NUM|NO\.?)\b',
        r'\b(DE|OF|DEL|THE)\b',
        r'[^\w\s]',  # Símbolos especiales
    ]
    
    # Patrones que sugieren que es un precinto válido
    POSITIVE_INDICATORS = [
        (r'^[A-Z]{2,4}\d{4,8}$', 3.0),  # Formato típico: ABC1234, WK01305
        (r'^\d{6,8}$', 2.8),            # Solo números largos: 0048604
        (r'^[A-Z]+\d+[A-Z]*$', 2.5),    # Mixto alfanumérico
        (r'^\d+[A-Z]+\d*$', 2.0),       # Número-letras-número
        (r'^[A-Z]{2,}\d{4,}$', 2.8),    # 2+ letras, 4+ números
        (r'\d$', 1.5),                  # Termina en dígito
        (r'^[A-Z]', 1.2),               # Empieza con letra
        (r'^\d{5,}$', 1.8),             # Números de 5+ dígitos
    ]
    
    def __init__(self):
        self.blacklist_regex = [re.compile(p, re.IGNORECASE) for p in self.BLACKLIST_PATTERNS]
        self.noise_regex = [re.compile(p, re.IGNORECASE) for p in self.NOISE_PATTERNS]
        
    def detect_precintos(self, texto: str) -> List[PrecintoCandidate]:
        """
        Detecta candidatos a precinto en el texto con scoring de confianza.
        """
        if not texto:
            return []
            
        # Normalizar texto
        texto_limpio = self._normalize_text(texto)
        
        # Extraer candidatos
        candidatos = self._extract_candidates(texto_limpio)
        
        # Filtrar y puntuar
        candidatos_validos = []
        for candidato in candidatos:
            if self._is_valid_candidate(candidato):
                confidence = self._calculate_confidence(candidato)
                if confidence > 0.5:  # Umbral mínimo
                    candidatos_validos.append(PrecintoCandidate(
                        text=candidato['text'],
                        confidence=confidence,
                        position=candidato['position'],
                        reasons=candidato['reasons']
                    ))
        
        # Ordenar por confianza
        return sorted(candidatos_validos, key=lambda x: x.confidence, reverse=True)
    
    def _normalize_text(self, texto: str) -> str:
        """Normaliza el texto para procesamiento."""
        # NFKC para caracteres Unicode
        texto = unicodedata.normalize("NFKC", texto)
        
        # Remover ruido común
        for pattern in self.noise_regex:
            texto = pattern.sub(' ', texto)
        
        # Limpiar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto.upper()
    
    def _extract_candidates(self, texto: str) -> List[Dict]:
        """Extrae candidatos potenciales del texto."""
        candidatos = []
        
        # 1. Tokens alfanuméricos individuales
        for match in re.finditer(r'[A-Z0-9]{4,20}', texto):
            candidatos.append({
                'text': match.group(),
                'position': match.span(),
                'reasons': ['token_alfanumerico'],
                'source': 'individual'
            })
        
        # 2. Tokens separados que podrían ser un precinto
        tokens = re.findall(r'[A-Z0-9]+', texto)
        for i in range(len(tokens) - 1):
            combined = tokens[i] + tokens[i + 1]
            if 5 <= len(combined) <= 20:
                candidatos.append({
                    'text': combined,
                    'position': (0, len(combined)),  # Aproximado
                    'reasons': ['tokens_combinados'],
                    'source': 'combined'
                })
        
        # 3. Secuencias con separadores mínimos
        for match in re.finditer(r'[A-Z0-9]+[\s\-\.]{0,2}[A-Z0-9]+', texto):
            clean = re.sub(r'[\s\-\.]', '', match.group())
            if 5 <= len(clean) <= 20:
                candidatos.append({
                    'text': clean,
                    'position': match.span(),
                    'reasons': ['secuencia_separada'],
                    'source': 'separated'
                })
        
        return candidatos
    
    def _is_valid_candidate(self, candidato: Dict) -> bool:
        """Verifica si un candidato pasa los filtros básicos."""
        text = candidato['text']
        
        # Verificar blacklist
        for pattern in self.blacklist_regex:
            if pattern.match(text):
                return False
        
        # Debe tener al menos un número, y opcionalmente letras
        if not re.search(r'\d', text):
            return False
        
        # Si es solo números, debe tener al menos 5 dígitos
        if text.isdigit() and len(text) < 5:
            return False
        
        # Longitud razonable
        if not (5 <= len(text) <= 20):
            return False
        
        # No debe ser solo letras (pero sí puede ser solo números si son suficientes)
        if text.isalpha():
            return False
        
        return True
    
    def _calculate_confidence(self, candidato: Dict) -> float:
        """Calcula la confianza de que sea un precinto válido."""
        text = candidato['text']
        confidence = 0.0
        reasons = candidato['reasons'].copy()
        
        # Aplicar indicadores positivos
        for pattern, score in self.POSITIVE_INDICATORS:
            if re.match(pattern, text):
                confidence += score
                reasons.append(f'pattern_{pattern}')
        
        # Bonificaciones adicionales
        if len(text) >= 6:
            confidence += 0.5
            reasons.append('longitud_adecuada')
        
        if re.search(r'[A-Z]{2,}', text) and re.search(r'\d{2,}', text):
            confidence += 1.0
            reasons.append('mixto_balanceado')
        
        # Penalizaciones
        if len(re.findall(r'(.)\1{3,}', text)) > 0:  # Repeticiones largas
            confidence -= 1.0
            reasons.append('repeticiones_sospechosas')
        
        if text.startswith('0') or text.endswith('0'):
            confidence -= 0.3
            reasons.append('ceros_extremos')
        
        # Normalizar a 0-1
        confidence = max(0.0, min(1.0, confidence / 5.0))
        
        candidato['reasons'] = reasons
        return confidence


def limpiar_precinto_mejorado(texto: Optional[str]) -> str:
    """
    Función mejorada para limpiar precintos con mayor precisión.
    Reemplaza la función original con mejor detección.
    """
    if not texto:
        return "NO DETECTADO"
    
    detector = PrecintoDetector()
    candidatos = detector.detect_precintos(texto)
    
    if not candidatos:
        return "NO DETECTADO"
    
    # Retornar el candidato con mayor confianza
    mejor_candidato = candidatos[0]
    
    # Si la confianza es muy baja, ser conservador
    if mejor_candidato.confidence < 0.7:
        return "NO DETECTADO"
    
    return mejor_candidato.text


# Función de compatibilidad con el código existente
def get_precinto_detection_info(texto: Optional[str]) -> Dict:
    """
    Función auxiliar que retorna información detallada de la detección.
    Útil para debugging y logging.
    """
    if not texto:
        return {
            "precinto": "NO DETECTADO",
            "confianza": 0.0,
            "candidatos": [],
            "razon": "texto_vacio"
        }
    
    detector = PrecintoDetector()
    candidatos = detector.detect_precintos(texto)
    
    if not candidatos:
        return {
            "precinto": "NO DETECTADO",
            "confianza": 0.0,
            "candidatos": [],
            "razon": "sin_candidatos_validos"
        }
    
    mejor = candidatos[0]
    return {
        "precinto": mejor.text if mejor.confidence >= 0.7 else "NO DETECTADO",
        "confianza": mejor.confidence,
        "candidatos": [
            {
                "texto": c.text,
                "confianza": c.confidence,
                "razones": c.reasons
            } for c in candidatos[:3]  # Top 3
        ],
        "razon": "detectado" if mejor.confidence >= 0.7 else "confianza_baja"
    }
