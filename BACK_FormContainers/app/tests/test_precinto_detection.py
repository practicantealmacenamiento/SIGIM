"""
Tests para el sistema mejorado de detección de precintos.
"""

import pytest
from app.domain.precinto_rules import PrecintoDetector, limpiar_precinto_mejorado, get_precinto_detection_info


class TestPrecintoDetector:
    """Tests para la clase PrecintoDetector."""
    
    def setup_method(self):
        self.detector = PrecintoDetector()
    
    def test_precinto_tipico_formato_abc123(self):
        """Test para formato típico ABC1234."""
        texto = "PRECINTO: TDM38816"
        candidatos = self.detector.detect_precintos(texto)
        
        assert len(candidatos) > 0
        assert candidatos[0].text == "TDM38816"
        assert candidatos[0].confidence > 0.7
    
    def test_precinto_con_ruido(self):
        """Test con texto ruidoso alrededor."""
        texto = "NUMERO DE PRECINTO TDM38816 SEGURIDAD"
        candidatos = self.detector.detect_precintos(texto)
        
        assert len(candidatos) > 0
        assert candidatos[0].text == "TDM38816"
    
    def test_precinto_separado(self):
        """Test con precinto separado por espacios."""
        texto = "TDM 388 16"
        candidatos = self.detector.detect_precintos(texto)
        
        assert len(candidatos) > 0
        assert "TDM38816" in [c.text for c in candidatos]
    
    def test_no_detectar_placa_vehicular(self):
        """No debe detectar placas vehiculares como precintos."""
        texto = "PLACA ABC123"
        candidatos = self.detector.detect_precintos(texto)
        
        # No debería detectar la placa como precinto
        assert len([c for c in candidatos if c.text == "ABC123"]) == 0
    
    def test_no_detectar_contenedor_iso(self):
        """No debe detectar contenedores ISO como precintos."""
        texto = "CONTENEDOR ABCD1234567"
        candidatos = self.detector.detect_precintos(texto)
        
        # No debería detectar el contenedor como precinto
        assert len([c for c in candidatos if c.text == "ABCD1234567"]) == 0
    
    def test_precinto_formato_mixto(self):
        """Test para formatos mixtos número-letra-número."""
        texto = "123ABC456"
        candidatos = self.detector.detect_precintos(texto)
        
        assert len(candidatos) > 0
        assert candidatos[0].text == "123ABC456"
    
    def test_texto_vacio(self):
        """Test con texto vacío."""
        candidatos = self.detector.detect_precintos("")
        assert len(candidatos) == 0
        
        candidatos = self.detector.detect_precintos(None)
        assert len(candidatos) == 0
    
    def test_solo_numeros_no_valido(self):
        """Solo números no debe ser válido."""
        texto = "123456789"
        candidatos = self.detector.detect_precintos(texto)
        
        # Puede detectar candidatos pero con baja confianza
        candidatos_altos = [c for c in candidatos if c.confidence > 0.5]
        assert len(candidatos_altos) == 0
    
    def test_solo_letras_no_valido(self):
        """Solo letras no debe ser válido."""
        texto = "ABCDEFGH"
        candidatos = self.detector.detect_precintos(texto)
        
        candidatos_altos = [c for c in candidatos if c.confidence > 0.5]
        assert len(candidatos_altos) == 0


class TestLimpiarPrecintoMejorado:
    """Tests para la función limpiar_precinto_mejorado."""
    
    def test_precinto_valido_simple(self):
        """Test con precinto válido simple."""
        resultado = limpiar_precinto_mejorado("TDM38816")
        assert resultado == "TDM38816"
    
    def test_precinto_con_ruido(self):
        """Test con ruido alrededor del precinto."""
        resultado = limpiar_precinto_mejorado("PRECINTO NUMERO: TDM38816 SEGURIDAD")
        assert resultado == "TDM38816"
    
    def test_precinto_separado(self):
        """Test con precinto separado."""
        resultado = limpiar_precinto_mejorado("TDM 388 16")
        assert resultado == "TDM38816"
    
    def test_texto_sin_precinto(self):
        """Test con texto que no contiene precinto."""
        resultado = limpiar_precinto_mejorado("SOLO TEXTO SIN NUMEROS")
        assert resultado == "NO DETECTADO"
    
    def test_placa_no_detectada_como_precinto(self):
        """Placa vehicular no debe ser detectada como precinto."""
        resultado = limpiar_precinto_mejorado("PLACA ABC123")
        assert resultado == "NO DETECTADO"
    
    def test_contenedor_no_detectado_como_precinto(self):
        """Contenedor ISO no debe ser detectado como precinto."""
        resultado = limpiar_precinto_mejorado("CONTENEDOR ABCD1234567")
        assert resultado == "NO DETECTADO"
    
    def test_texto_vacio(self):
        """Test con texto vacío o None."""
        assert limpiar_precinto_mejorado("") == "NO DETECTADO"
        assert limpiar_precinto_mejorado(None) == "NO DETECTADO"
        assert limpiar_precinto_mejorado("   ") == "NO DETECTADO"
    
    def test_precinto_con_guiones(self):
        """Test con precinto que tiene guiones."""
        resultado = limpiar_precinto_mejorado("TDM-388-16")
        assert resultado == "TDM38816"
    
    def test_precinto_con_puntos(self):
        """Test con precinto que tiene puntos."""
        resultado = limpiar_precinto_mejorado("TDM.388.16")
        assert resultado == "TDM38816"


class TestGetPrecintoDetectionInfo:
    """Tests para la función de información detallada."""
    
    def test_info_precinto_valido(self):
        """Test información detallada para precinto válido."""
        info = get_precinto_detection_info("TDM38816")
        
        assert info["precinto"] == "TDM38816"
        assert info["confianza"] > 0.7
        assert info["razon"] == "detectado"
        assert len(info["candidatos"]) > 0
    
    def test_info_precinto_invalido(self):
        """Test información detallada para texto sin precinto."""
        info = get_precinto_detection_info("SOLO TEXTO")
        
        assert info["precinto"] == "NO DETECTADO"
        assert info["confianza"] == 0.0
        assert info["razon"] in ["sin_candidatos_validos", "confianza_baja"]
    
    def test_info_texto_vacio(self):
        """Test información detallada para texto vacío."""
        info = get_precinto_detection_info("")
        
        assert info["precinto"] == "NO DETECTADO"
        assert info["confianza"] == 0.0
        assert info["razon"] == "texto_vacio"
        assert len(info["candidatos"]) == 0


# Tests de integración con casos reales
class TestCasosReales:
    """Tests con casos que podrían ocurrir en producción."""
    
    @pytest.mark.parametrize("texto_ocr,precinto_esperado", [
        ("PRECINTO DE SEGURIDAD: TDM38816", "TDM38816"),
        ("SEAL NUMBER: ABC12345", "ABC12345"),
        ("TDM 388 16", "TDM38816"),
        ("NUMERO: TDM-388-16", "TDM38816"),
        ("123ABC456DEF", "123ABC456"),  # Debería tomar la parte más probable
        ("PLACA ABC123 PRECINTO TDM38816", "TDM38816"),  # Debe ignorar la placa
        ("CONTENEDOR ABCD1234567 SELLO XYZ789", "XYZ789"),  # Debe ignorar contenedor
    ])
    def test_casos_reales(self, texto_ocr, precinto_esperado):
        """Test con casos reales de OCR."""
        resultado = limpiar_precinto_mejorado(texto_ocr)
        assert resultado == precinto_esperado
    
    @pytest.mark.parametrize("texto_ocr", [
        "SOLO TEXTO SIN NUMEROS",
        "123456",  # Solo números
        "ABCDEF",  # Solo letras
        "PLACA ABC123",  # Solo placa
        "CONTENEDOR ABCD1234567",  # Solo contenedor
        "",
        None,
    ])
    def test_casos_no_detectados(self, texto_ocr):
        """Test con casos que no deberían detectar precinto."""
        resultado = limpiar_precinto_mejorado(texto_ocr)
        assert resultado == "NO DETECTADO"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
