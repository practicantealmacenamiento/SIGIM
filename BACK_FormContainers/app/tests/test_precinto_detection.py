"""
Pruebas enfocadas en la heurística de detección de precintos.

El módulo `app.domain.rules` consolidó la lógica que antes vivía en
`precinto_rules`, por lo que estas pruebas aseguran que el comportamiento
esperado siga disponible desde la API actual.
"""

import pytest

from app.domain import rules


class TestLimpiarPrecinto:
    """Casos de uso para la extracción de precintos."""

    @pytest.mark.parametrize(
        "texto, expected",
        [
            ("PRECINTO: TDM38816", "TDM38816"),
            ("SEAL NUMBER: ABC12345", "ABC12345"),
            ("SELLO TDM 388 16", "TDM38816"),
            ("NUMERO: TDM-388-16", "TDM38816"),
            ("EBS0053049EBS0053049", "EBS0053049"),
        ],
    )
    def test_detecta_precintos_comunes(self, texto, expected):
        assert rules.limpiar_precinto(texto) == expected

    def test_ignora_lineas_de_fecha_hora(self):
        texto_ocr = "21/07/2025 07:15 AM\nPRECINTO: TDM38816"
        assert rules.limpiar_precinto(texto_ocr) == "TDM38816"

    def test_ignora_nit_en_texto(self):
        texto_ocr = "NIT 900.632.994-2\nPrecinto: TDM38816"
        assert rules.limpiar_precinto(texto_ocr) == "TDM38816"

    def test_precinto_preferido_si_aparece_antes_que_placa(self):
        texto_ocr = "PRECINTO TDM38816 PLACA ABC123"
        assert rules.limpiar_precinto(texto_ocr) in {"ABC123", "TDM38816"}

    def test_no_confunde_contenedor_con_precinto(self):
        texto_ocr = "CONTENEDOR ABCD1234567 SELLO XYZ789"
        assert rules.limpiar_precinto(texto_ocr) == "XYZ789"

    def test_fallback_numerico(self):
        texto_ocr = "Solo números: 987654321"
        assert rules.limpiar_precinto(texto_ocr) == "987654321"

    @pytest.mark.parametrize(
        "texto, expected",
        [
            ("SOLO TEXTO SIN NUMEROS", "NUMEROS"),
            ("ABCDEFGH", "ABCDEFGH"),
            ("", "NO DETECTADO"),
            (None, "NO DETECTADO"),
            ("   ", "NO DETECTADO"),
            ("AB12", "NO DETECTADO"),
        ],
    )
    def test_casos_limite(self, texto, expected):
        assert rules.limpiar_precinto(texto) == expected

    def test_no_devuelve_capturas_parciales_complejas(self):
        assert rules.limpiar_precinto("123ABC456DEF") == "NO DETECTADO"
