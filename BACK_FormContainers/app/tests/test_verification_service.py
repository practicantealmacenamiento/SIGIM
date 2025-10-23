"""
Pruebas unitarias para VerificationService con mocks.

Estas pruebas verifican:
1. Orquestación de casos de uso de verificación OCR
2. Interacción correcta con TextExtractorPort
3. Manejo de errores y excepciones específicas
4. Aplicación de reglas de dominio por semantic_tag
5. Uso de mocks para aislar dependencias externas
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from typing import Dict

from app.application.verification import VerificationService
from app.domain.ports import TextExtractorPort
from app.domain.repositories import QuestionRepository
from app.domain.entities import Question
from app.domain.exceptions import (
    BusinessRuleViolationError,
    InvalidImageError,
    ExtractionError,
    EntityNotFoundError,
)


class TestVerificationService(unittest.TestCase):
    """Pruebas para VerificationService."""

    def setUp(self):
        """Configuración inicial para cada prueba."""
        self.mock_text_extractor = Mock(spec=TextExtractorPort)
        self.mock_question_repo = Mock(spec=QuestionRepository)
        
        self.service = VerificationService(
            text_extractor=self.mock_text_extractor,
            question_repo=self.mock_question_repo
        )

    def test_verificar_placa_success(self):
        """Debe verificar placa correctamente cuando OCR detecta texto válido."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        ocr_text = "ABC123 COLOMBIA"
        
        self.mock_text_extractor.extract_text.return_value = ocr_text
        
        # Act
        with patch('app.domain.rules.normalizar_placa') as mock_normalizar:
            mock_normalizar.return_value = "ABC123"
            
            result = self.service.verificar_placa(imagen_bytes)
        
        # Assert
        self.mock_text_extractor.extract_text.assert_called_once_with(imagen_bytes)
        mock_normalizar.assert_called_once_with(ocr_text)
        
        expected_result = {
            "ocr_raw": ocr_text,
            "placa": "ABC123",
            "valido": True
        }
        self.assertEqual(result, expected_result)

    def test_verificar_placa_no_detectada(self):
        """Debe manejar caso cuando no se detecta placa válida."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        ocr_text = "Texto sin placa válida"
        
        self.mock_text_extractor.extract_text.return_value = ocr_text
        
        # Act
        with patch('app.domain.rules.normalizar_placa') as mock_normalizar:
            mock_normalizar.return_value = "NO_DETECTADA"
            
            result = self.service.verificar_placa(imagen_bytes)
        
        # Assert
        expected_result = {
            "ocr_raw": ocr_text,
            "placa": None,
            "valido": False
        }
        self.assertEqual(result, expected_result)

    def test_verificar_precinto_success(self):
        """Debe verificar precinto correctamente."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        ocr_text = "PRECINTO: 123456789"
        
        self.mock_text_extractor.extract_text.return_value = ocr_text
        
        # Act
        with patch('app.domain.rules.limpiar_precinto') as mock_limpiar:
            mock_limpiar.return_value = "123456789"
            
            result = self.service.verificar_precinto(imagen_bytes)
        
        # Assert
        self.mock_text_extractor.extract_text.assert_called_once_with(imagen_bytes)
        mock_limpiar.assert_called_once_with(ocr_text)
        
        expected_result = {
            "ocr_raw": ocr_text,
            "precinto": "123456789",
            "valido": True
        }
        self.assertEqual(result, expected_result)

    def test_verificar_precinto_no_detectado(self):
        """Debe manejar caso cuando no se detecta precinto."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        ocr_text = "Texto sin precinto"
        
        self.mock_text_extractor.extract_text.return_value = ocr_text
        
        # Act
        with patch('app.domain.rules.limpiar_precinto') as mock_limpiar:
            mock_limpiar.return_value = "NO DETECTADO"
            
            result = self.service.verificar_precinto(imagen_bytes)
        
        # Assert
        expected_result = {
            "ocr_raw": ocr_text,
            "precinto": None,
            "valido": False
        }
        self.assertEqual(result, expected_result)

    def test_verificar_contenedor_success(self):
        """Debe verificar contenedor correctamente."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        ocr_text = "CONTAINER: ABCD1234567"
        
        self.mock_text_extractor.extract_text.return_value = ocr_text
        
        # Act
        with patch('app.domain.rules.extraer_contenedor') as mock_extraer, \
             patch('app.domain.rules.validar_iso6346') as mock_validar:
            
            mock_extraer.return_value = "ABCD1234567"
            mock_validar.return_value = True
            
            result = self.service.verificar_contenedor(imagen_bytes)
        
        # Assert
        self.mock_text_extractor.extract_text.assert_called_once_with(imagen_bytes)
        mock_extraer.assert_called_once_with(ocr_text)
        mock_validar.assert_called_once_with("ABCD1234567")
        
        expected_result = {
            "ocr_raw": ocr_text,
            "contenedor": "ABCD1234567",
            "valido": True
        }
        self.assertEqual(result, expected_result)

    def test_verificar_contenedor_invalid_iso6346(self):
        """Debe rechazar contenedor con formato ISO6346 inválido."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        ocr_text = "CONTAINER: INVALID123"
        
        self.mock_text_extractor.extract_text.return_value = ocr_text
        
        # Act
        with patch('app.domain.rules.extraer_contenedor') as mock_extraer, \
             patch('app.domain.rules.validar_iso6346') as mock_validar:
            
            mock_extraer.return_value = "INVALID123"
            mock_validar.return_value = False  # Invalid format
            
            result = self.service.verificar_contenedor(imagen_bytes)
        
        # Assert
        expected_result = {
            "ocr_raw": ocr_text,
            "contenedor": None,
            "valido": False
        }
        self.assertEqual(result, expected_result)

    def test_verify_with_question_success(self):
        """Debe verificar con pregunta correctamente."""
        # Arrange
        question_id = uuid4()
        mock_image_file = Mock()
        mock_image_file.read.return_value = b"fake_image_data"
        mock_image_file.seek = Mock()
        
        # Mock question with placa semantic_tag
        mock_question = Mock()
        mock_question.semantic_tag = "placa"
        self.mock_question_repo.get.return_value = mock_question
        
        self.mock_text_extractor.extract_text.return_value = "ABC123 COLOMBIA"
        
        # Act
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical, \
             patch('app.domain.rules.normalizar_placa') as mock_normalizar:
            
            mock_canonical.return_value = "placa"
            mock_normalizar.return_value = "ABC123"
            
            result = self.service.verify_with_question(question_id, mock_image_file)
        
        # Assert
        self.mock_question_repo.get.assert_called_once_with(question_id)
        mock_image_file.seek.assert_called_once_with(0)
        mock_image_file.read.assert_called_once()
        
        expected_result = {
            "ocr_raw": "ABC123 COLOMBIA",
            "placa": "ABC123",
            "valido": True,
            "semantic_tag": "placa"
        }
        self.assertEqual(result, expected_result)

    def test_verify_with_question_not_found(self):
        """Debe lanzar EntityNotFoundError si pregunta no existe."""
        # Arrange
        question_id = uuid4()
        mock_image_file = Mock()
        
        self.mock_question_repo.get.return_value = None
        
        # Act & Assert
        with self.assertRaises(EntityNotFoundError) as context:
            self.service.verify_with_question(question_id, mock_image_file)
        
        self.assertIn(f"Pregunta con id {question_id} no encontrada", str(context.exception))
        self.assertEqual(context.exception.entity_type, "Question")
        self.assertEqual(context.exception.entity_id, str(question_id))

    def test_verify_with_question_no_image(self):
        """Debe lanzar InvalidImageError si no se proporciona imagen."""
        # Arrange
        question_id = uuid4()
        
        # Act & Assert
        with self.assertRaises(InvalidImageError) as context:
            self.service.verify_with_question(question_id, None)
        
        self.assertIn("No se proporcionó ninguna imagen", str(context.exception))

    def test_verify_with_question_empty_image(self):
        """Debe lanzar InvalidImageError si imagen está vacía."""
        # Arrange
        question_id = uuid4()
        mock_image_file = Mock()
        mock_image_file.read.return_value = b""  # Empty image
        
        mock_question = Mock()
        mock_question.semantic_tag = "placa"
        self.mock_question_repo.get.return_value = mock_question
        
        # Act & Assert
        with self.assertRaises(InvalidImageError) as context:
            self.service.verify_with_question(question_id, mock_image_file)

        self.assertIn("Imagen vacía", str(context.exception))

    def test_verify_with_question_requires_semantic_tag(self):
        """Debe rechazar verificación cuando la pregunta no tiene semantic_tag permitido."""
        question_id = uuid4()
        mock_image_file = Mock()
        mock_image_file.seek = Mock()
        mock_image_file.read.return_value = b"fake_image_data"

        mock_question = Mock()
        mock_question.semantic_tag = None  # Sin tag configurado
        self.mock_question_repo.get.return_value = mock_question

        with patch("app.domain.rules.canonical_semantic_tag", return_value="none"):
            with self.assertRaises(BusinessRuleViolationError) as ctx:
                self.service.verify_with_question(question_id, mock_image_file)

        self.assertIn("semantic_tag", ctx.exception.message)

    def test_verificar_universal_placa_tag(self):
        """Debe usar verificación de placa para semantic_tag 'placa'."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "ABC123"
        
        # Act
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical, \
             patch('app.domain.rules.normalizar_placa') as mock_normalizar:
            
            mock_canonical.return_value = "placa"
            mock_normalizar.return_value = "ABC123"
            
            result = self.service.verificar_universal("placa", imagen_bytes)
        
        # Assert
        mock_canonical.assert_called_once_with("placa")
        mock_normalizar.assert_called_once_with("ABC123")
        
        expected_result = {
            "ocr_raw": "ABC123",
            "placa": "ABC123",
            "valido": True
        }
        self.assertEqual(result, expected_result)

    def test_verificar_universal_precinto_tag(self):
        """Debe usar verificación de precinto para semantic_tag 'precinto'."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "123456789"
        
        # Act
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical, \
             patch('app.domain.rules.limpiar_precinto') as mock_limpiar:
            
            mock_canonical.return_value = "precinto"
            mock_limpiar.return_value = "123456789"
            
            result = self.service.verificar_universal("precinto", imagen_bytes)
        
        # Assert
        mock_canonical.assert_called_once_with("precinto")
        mock_limpiar.assert_called_once_with("123456789")
        
        expected_result = {
            "ocr_raw": "123456789",
            "precinto": "123456789",
            "valido": True
        }
        self.assertEqual(result, expected_result)

    def test_verificar_universal_contenedor_tag(self):
        """Debe usar verificación de contenedor para semantic_tag 'contenedor'."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "ABCD1234567"
        
        # Act
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical, \
             patch('app.domain.rules.extraer_contenedor') as mock_extraer, \
             patch('app.domain.rules.validar_iso6346') as mock_validar:
            
            mock_canonical.return_value = "contenedor"
            mock_extraer.return_value = "ABCD1234567"
            mock_validar.return_value = True
            
            result = self.service.verificar_universal("contenedor", imagen_bytes)
        
        # Assert
        mock_canonical.assert_called_once_with("contenedor")
        mock_extraer.assert_called_once_with("ABCD1234567")
        mock_validar.assert_called_once_with("ABCD1234567")
        
        expected_result = {
            "ocr_raw": "ABCD1234567",
            "contenedor": "ABCD1234567",
            "valido": True
        }
        self.assertEqual(result, expected_result)

    def test_verificar_universal_fallback_generic(self):
        """Debe usar verificación genérica para semantic_tag desconocido."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "Texto genérico"
        
        # Act
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical:
            mock_canonical.return_value = "unknown"
            
            result = self.service.verificar_universal("unknown", imagen_bytes)
        
        # Assert
        mock_canonical.assert_called_once_with("unknown")
        
        expected_result = {
            "ocr_raw": "Texto genérico",
            "valido": True  # Has non-empty text
        }
        self.assertEqual(result, expected_result)

    def test_verificar_universal_fallback_empty_text(self):
        """Debe marcar como inválido cuando texto OCR está vacío."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "   "  # Only whitespace
        
        # Act
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical:
            mock_canonical.return_value = "unknown"
            
            result = self.service.verificar_universal("unknown", imagen_bytes)
        
        # Assert
        expected_result = {
            "ocr_raw": "",  # Stripped whitespace
            "valido": False  # Empty after strip
        }
        self.assertEqual(result, expected_result)

    def test_ocr_empty_image_raises_error(self):
        """Debe lanzar InvalidImageError para imagen vacía en _ocr."""
        # Arrange
        imagen_bytes = b""
        
        # Act & Assert
        with self.assertRaises(InvalidImageError) as context:
            self.service._ocr(imagen_bytes)
        
        self.assertIn("Imagen vacía", str(context.exception))
        self.assertEqual(context.exception.image_size, 0)

    def test_ocr_extraction_failure_raises_error(self):
        """Debe lanzar ExtractionError cuando OCR falla."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.side_effect = Exception("OCR service failed")
        
        # Act & Assert
        with self.assertRaises(ExtractionError) as context:
            self.service._ocr(imagen_bytes)
        
        self.assertIn("OCR falló: OCR service failed", str(context.exception))
        self.assertEqual(context.exception.service_name, "text_extractor")
        self.assertEqual(context.exception.error_code, "Exception")

    def test_ocr_success_strips_whitespace(self):
        """Debe limpiar espacios en blanco del resultado OCR."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "  Texto con espacios  \n"
        
        # Act
        result = self.service._ocr(imagen_bytes)
        
        # Assert
        self.assertEqual(result, "Texto con espacios")
        self.mock_text_extractor.extract_text.assert_called_once_with(imagen_bytes)

    def test_prepare_image_data_success(self):
        """Debe preparar datos de imagen correctamente."""
        # Arrange
        mock_image_file = Mock()
        mock_image_file.read.return_value = b"fake_image_data"
        mock_image_file.seek = Mock()
        
        # Act
        result = self.service._prepare_image_data(mock_image_file)
        
        # Assert
        mock_image_file.seek.assert_called_once_with(0)
        mock_image_file.read.assert_called_once()
        self.assertEqual(result, b"fake_image_data")

    def test_prepare_image_data_no_seek_method(self):
        """Debe manejar archivos sin método seek."""
        # Arrange
        mock_image_file = Mock()
        mock_image_file.read.return_value = b"fake_image_data"
        del mock_image_file.seek  # No seek method
        
        # Act
        result = self.service._prepare_image_data(mock_image_file)
        
        # Assert
        mock_image_file.read.assert_called_once()
        self.assertEqual(result, b"fake_image_data")

    def test_prepare_image_data_seek_fails(self):
        """Debe continuar si seek falla."""
        # Arrange
        mock_image_file = Mock()
        mock_image_file.read.return_value = b"fake_image_data"
        mock_image_file.seek.side_effect = Exception("Seek failed")
        
        # Act
        result = self.service._prepare_image_data(mock_image_file)
        
        # Assert
        mock_image_file.read.assert_called_once()
        self.assertEqual(result, b"fake_image_data")

    def test_dependency_injection(self):
        """Debe verificar que el servicio use inyección de dependencias correctamente."""
        # Verify dependencies are injected
        self.assertEqual(self.service.text_extractor, self.mock_text_extractor)
        self.assertEqual(self.service.question_repo, self.mock_question_repo)

    def test_service_orchestrates_domain_rules(self):
        """Debe verificar que el servicio orqueste reglas de dominio correctamente."""
        # Arrange
        imagen_bytes = b"fake_image_data"
        self.mock_text_extractor.extract_text.return_value = "ABC123"
        
        # Act
        with patch('app.domain.rules.normalizar_placa') as mock_normalizar:
            mock_normalizar.return_value = "ABC123"
            
            result = self.service.verificar_placa(imagen_bytes)
        
        # Assert
        # Service should orchestrate: OCR extraction -> domain rule application
        self.mock_text_extractor.extract_text.assert_called_once_with(imagen_bytes)
        mock_normalizar.assert_called_once_with("ABC123")
        self.assertTrue(result["valido"])

    def test_service_handles_multiple_semantic_tags(self):
        """Debe manejar múltiples semantic_tags correctamente."""
        # Test that service can handle different semantic tags in same session
        imagen_bytes = b"fake_image_data"
        
        # Test placa
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical, \
             patch('app.domain.rules.normalizar_placa') as mock_normalizar:
            
            self.mock_text_extractor.extract_text.return_value = "ABC123"
            mock_canonical.return_value = "placa"
            mock_normalizar.return_value = "ABC123"
            
            result_placa = self.service.verificar_universal("placa", imagen_bytes)
            self.assertIn("placa", result_placa)
        
        # Test precinto
        with patch('app.domain.rules.canonical_semantic_tag') as mock_canonical, \
             patch('app.domain.rules.limpiar_precinto') as mock_limpiar:
            
            self.mock_text_extractor.extract_text.return_value = "123456"
            mock_canonical.return_value = "precinto"
            mock_limpiar.return_value = "123456"
            
            result_precinto = self.service.verificar_universal("precinto", imagen_bytes)
            self.assertIn("precinto", result_precinto)


class TestVerificationServiceIntegration(unittest.TestCase):
    """Pruebas de integración para VerificationService."""

    def test_service_without_question_repo_initialization(self):
        """Debe verificar que el servicio puede inicializarse sin question_repo."""
        # Arrange & Act
        mock_text_extractor = Mock(spec=TextExtractorPort)
        service = VerificationService(text_extractor=mock_text_extractor)
        
        # Assert
        self.assertEqual(service.text_extractor, mock_text_extractor)
        self.assertIsNone(service.question_repo)

    def test_service_error_propagation(self):
        """Debe propagar errores de dependencias correctamente."""
        # Arrange
        mock_text_extractor = Mock(spec=TextExtractorPort)
        mock_question_repo = Mock(spec=QuestionRepository)
        
        service = VerificationService(
            text_extractor=mock_text_extractor,
            question_repo=mock_question_repo
        )
        
        # Test OCR error propagation
        mock_text_extractor.extract_text.side_effect = RuntimeError("OCR service down")
        
        # Act & Assert
        with self.assertRaises(ExtractionError):
            service._ocr(b"fake_image_data")

    def test_service_maintains_state_isolation(self):
        """Debe mantener aislamiento de estado entre llamadas."""
        # Arrange
        mock_text_extractor = Mock(spec=TextExtractorPort)
        service = VerificationService(text_extractor=mock_text_extractor)
        
        # Act - Multiple calls should not interfere
        mock_text_extractor.extract_text.return_value = "First call"
        result1 = service._ocr(b"image1")
        
        mock_text_extractor.extract_text.return_value = "Second call"
        result2 = service._ocr(b"image2")
        
        # Assert
        self.assertEqual(result1, "First call")
        self.assertEqual(result2, "Second call")
        self.assertEqual(mock_text_extractor.extract_text.call_count, 2)


if __name__ == '__main__':
    unittest.main()
