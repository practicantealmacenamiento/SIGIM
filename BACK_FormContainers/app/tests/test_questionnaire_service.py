"""
Pruebas unitarias para QuestionnaireService con mocks.

Estas pruebas verifican:
1. Caso de uso "Guardar y Avanzar"
2. Validaciones de reglas de negocio
3. Manejo de archivos y límites
4. Lógica de ramificación
5. Orquestación de repositorios y puertos
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import replace
from uuid import uuid4, UUID
from typing import Optional

from app.application.questionnaire import QuestionnaireService
from app.application.commands import SaveAndAdvanceCommand, SaveAndAdvanceResult
from app.domain.entities import Answer, Submission, Question, Choice
from app.domain.exceptions import (
    EntityNotFoundError, 
    ValidationError, 
    BusinessRuleViolationError
)
from app.domain.ports.repositories import (
    AnswerRepository,
    SubmissionRepository, 
    QuestionRepository,
    ChoiceRepository
)
from app.domain.ports.external_ports import FileStorage


class TestQuestionnaireService(unittest.TestCase):
    """Pruebas para QuestionnaireService."""

    def setUp(self):
        """Configuración inicial para cada prueba."""
        self.mock_answer_repo = Mock(spec=AnswerRepository)
        self.mock_submission_repo = Mock(spec=SubmissionRepository)
        self.mock_question_repo = Mock(spec=QuestionRepository)
        self.mock_choice_repo = Mock(spec=ChoiceRepository)
        self.mock_storage = Mock(spec=FileStorage)
        
        self.service = QuestionnaireService(
            answer_repo=self.mock_answer_repo,
            submission_repo=self.mock_submission_repo,
            question_repo=self.mock_question_repo,
            choice_repo=self.mock_choice_repo,
            storage=self.mock_storage
        )

    def _make_question(self, **attrs):
        """Crea un Mock de question con valores por defecto seguros."""
        question = Mock()
        question.semantic_tag = attrs.pop("semantic_tag", "none")
        question.file_mode = attrs.pop("file_mode", "")
        for key, value in attrs.items():
            setattr(question, key, value)
        return question

    def test_save_and_advance_text_answer_success(self):
        """Debe guardar respuesta de texto y avanzar correctamente."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        next_question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Mi respuesta de texto"
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question
        mock_question = self._make_question(id=question_id, type="text", required=False)
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock next question
        self.mock_question_repo.next_in_questionnaire.return_value = next_question_id
        
        # Mock saved answer
        expected_answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Mi respuesta de texto"
        )
        self.mock_answer_repo.save.return_value = expected_answer
        
        # Act
        result = self.service.save_and_advance(cmd)
        
        # Assert
        self.assertIsInstance(result, SaveAndAdvanceResult)
        self.assertEqual(result.saved_answer, expected_answer)
        self.assertEqual(result.next_question_id, next_question_id)
        self.assertFalse(result.is_finished)
        
        # Verify repository calls
        self.mock_submission_repo.get.assert_called_once_with(submission_id)
        self.mock_question_repo.get.assert_called_once_with(question_id)
        self.mock_answer_repo.clear_for_question.assert_called_once_with(
            submission_id=submission_id, question_id=question_id
        )
        self.mock_answer_repo.delete_after_question.assert_called_once_with(
            submission_id=submission_id, question_id=question_id
        )
        self.mock_answer_repo.save.assert_called_once()

    def test_save_and_advance_choice_answer_success(self):
        """Debe guardar respuesta de opción múltiple correctamente."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        choice_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_choice_id=choice_id
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question
        mock_question = self._make_question(id=question_id, type="choice", required=False)
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock choice
        mock_choice = Mock()
        mock_choice.id = choice_id
        mock_choice.question_id = question_id
        mock_choice.branch_to = None
        mock_choice.branch_to_id = None
        self.mock_choice_repo.get.return_value = mock_choice
        
        # Mock next question
        next_question_id = uuid4()
        self.mock_question_repo.next_in_questionnaire.return_value = next_question_id
        
        # Mock saved answer
        expected_answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_choice_id=choice_id
        )
        self.mock_answer_repo.save.return_value = expected_answer
        
        # Act
        result = self.service.save_and_advance(cmd)
        
        # Assert
        self.assertEqual(result.saved_answer, expected_answer)
        self.assertEqual(result.next_question_id, next_question_id)
        self.mock_choice_repo.get.assert_called_once_with(choice_id)

    def test_save_and_advance_with_file_upload(self):
        """Debe guardar respuesta con archivo correctamente."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        mock_upload = Mock()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            uploads=[mock_upload]
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question (file type)
        mock_question = self._make_question(
            id=question_id,
            type="file",
            required=False,
            file_mode="image_ocr",
        )
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock storage
        expected_path = f"submissions/{submission_id}/file.jpg"
        self.mock_storage.save.return_value = expected_path
        
        # Mock saved answer
        expected_answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_file_path=expected_path
        )
        self.mock_answer_repo.save.return_value = expected_answer
        
        # Mock next question
        self.mock_question_repo.next_in_questionnaire.return_value = None  # Last question
        
        # Act
        result = self.service.save_and_advance(cmd)
        
        # Assert
        self.assertEqual(result.saved_answer, expected_answer)
        self.assertIsNone(result.next_question_id)
        self.assertTrue(result.is_finished)
        
        # Verify file storage
        self.mock_storage.save.assert_called_once_with(
            folder=f"submissions/{submission_id}",
            file_obj=mock_upload
        )

    def test_save_and_advance_submission_not_found(self):
        """Debe lanzar EntityNotFoundError si submission no existe."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Respuesta"
        )
        
        self.mock_submission_repo.get.return_value = None
        
        # Act & Assert
        with self.assertRaises(EntityNotFoundError) as context:
            self.service.save_and_advance(cmd)
        
        self.assertIn("Submission no encontrada", str(context.exception))
        self.assertEqual(context.exception.entity_type, "Submission")
        self.assertEqual(context.exception.entity_id, str(submission_id))

    def test_save_and_advance_question_not_found(self):
        """Debe lanzar EntityNotFoundError si question no existe."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Respuesta"
        )
        
        # Mock submission exists
        mock_submission = Mock()
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question doesn't exist
        self.mock_question_repo.get.return_value = None
        
        # Act & Assert
        with self.assertRaises(EntityNotFoundError) as context:
            self.service.save_and_advance(cmd)
        
        self.assertIn("Pregunta no encontrada", str(context.exception))
        self.assertEqual(context.exception.entity_type, "Question")

    def test_save_and_advance_choice_not_found(self):
        """Debe lanzar EntityNotFoundError si choice no existe."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        choice_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_choice_id=choice_id
        )
        
        # Mock submission and question exist
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        mock_question = self._make_question(id=question_id, type="choice")
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock choice doesn't exist
        self.mock_choice_repo.get.return_value = None
        
        # Act & Assert
        with self.assertRaises(EntityNotFoundError) as context:
            self.service.save_and_advance(cmd)
        
        self.assertIn("La opción indicada no existe", str(context.exception))
        self.assertEqual(context.exception.entity_type, "Choice")

    def test_save_and_advance_choice_wrong_question(self):
        """Debe lanzar BusinessRuleViolationError si choice no pertenece a question."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        choice_id = uuid4()
        other_question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_choice_id=choice_id
        )
        
        # Mock submission and question exist
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        mock_question = self._make_question(id=question_id, type="choice")
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock choice belongs to different question
        mock_choice = Mock()
        mock_choice.id = choice_id
        mock_choice.question_id = other_question_id  # Different question!
        self.mock_choice_repo.get.return_value = mock_choice
        
        # Act & Assert
        with self.assertRaises(BusinessRuleViolationError) as context:
            self.service.save_and_advance(cmd)
        
        self.assertIn("La opción no pertenece a la pregunta", str(context.exception))
        self.assertEqual(context.exception.rule_name, "choice_belongs_to_question")

    def test_save_and_advance_file_upload_not_allowed(self):
        """Debe lanzar BusinessRuleViolationError si question no acepta archivos."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        mock_upload = Mock()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            uploads=[mock_upload]
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question (text type - no files allowed)
        mock_question = self._make_question(id=question_id, type="text", required=False)
        self.mock_question_repo.get.return_value = mock_question
        
        # Act & Assert
        with self.assertRaises(BusinessRuleViolationError) as context:
            self.service.save_and_advance(cmd)
        
        self.assertIn("Esta pregunta no acepta archivos adjuntos", str(context.exception))
        self.assertEqual(context.exception.rule_name, "question_file_upload_not_allowed")

    def test_save_and_advance_required_question_empty(self):
        """Debe lanzar ValidationError si question requerida está vacía."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id
            # No answer_text, answer_choice_id, or uploads
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock required question
        mock_question = self._make_question(id=question_id, type="text", required=True)
        self.mock_question_repo.get.return_value = mock_question
        
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            self.service.save_and_advance(cmd)
        
        self.assertIn("La pregunta es obligatoria", str(context.exception))
        self.assertEqual(context.exception.field, "answer")

    def test_save_and_advance_file_limit_enforcement(self):
        """Debe limitar número de archivos según tipo de pregunta."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        mock_upload1 = Mock()
        mock_upload2 = Mock()
        mock_upload3 = Mock()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            uploads=[mock_upload1, mock_upload2, mock_upload3]  # 3 files
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question (OCR mode - max 1 file)
        mock_question = self._make_question(
            id=question_id,
            type="file",
            required=False,
            file_mode="image_ocr",
        )
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock storage and answer
        self.mock_storage.save.return_value = "path/to/file.jpg"
        expected_answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_file_path="path/to/file.jpg"
        )
        self.mock_answer_repo.save.return_value = expected_answer
        
        # Mock next question
        self.mock_question_repo.next_in_questionnaire.return_value = None
        
        # Act
        result = self.service.save_and_advance(cmd)
        
        # Assert
        # Should only save first file (limit enforced)
        self.mock_storage.save.assert_called_once_with(
            folder=f"submissions/{submission_id}",
            file_obj=mock_upload1  # Only first file
        )

    def test_save_and_advance_with_branching(self):
        """Debe seguir ramificación cuando choice tiene branch_to."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        choice_id = uuid4()
        branch_question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_choice_id=choice_id
        )
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        # Mock question
        mock_question = self._make_question(id=question_id, type="choice", required=False)
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock choice with branching
        mock_choice = Mock()
        mock_choice.id = choice_id
        mock_choice.question_id = question_id
        mock_choice.branch_to = branch_question_id  # Has branching!
        self.mock_choice_repo.get.return_value = mock_choice
        
        # Mock saved answer
        expected_answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_choice_id=choice_id
        )
        self.mock_answer_repo.save.return_value = expected_answer
        
        # Act
        result = self.service.save_and_advance(cmd)
        
        # Assert
        self.assertEqual(result.next_question_id, branch_question_id)
        self.assertFalse(result.is_finished)
        
        # Should NOT call next_in_questionnaire because branching takes precedence
        self.mock_question_repo.next_in_questionnaire.assert_not_called()

    def test_save_and_advance_truncate_future_disabled(self):
        """Debe no truncar respuestas futuras cuando force_truncate_future=False."""
        # Arrange
        submission_id = uuid4()
        question_id = uuid4()
        
        cmd = SaveAndAdvanceCommand(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Respuesta",
            force_truncate_future=False  # Disabled
        )
        
        # Mock submission and question
        mock_submission = Mock()
        mock_submission.id = submission_id
        self.mock_submission_repo.get.return_value = mock_submission
        
        mock_question = self._make_question(id=question_id, type="text", required=False)
        self.mock_question_repo.get.return_value = mock_question
        
        # Mock saved answer and next question
        expected_answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Respuesta"
        )
        self.mock_answer_repo.save.return_value = expected_answer
        self.mock_question_repo.next_in_questionnaire.return_value = None
        
        # Act
        result = self.service.save_and_advance(cmd)
        
        # Assert
        # Should NOT call delete_after_question
        self.mock_answer_repo.delete_after_question.assert_not_called()
        
        # Should still clear current question
        self.mock_answer_repo.clear_for_question.assert_called_once_with(
            submission_id=submission_id, question_id=question_id
        )

    def test_save_and_advance_dependency_injection(self):
        """Debe verificar que el servicio use inyección de dependencias correctamente."""
        # Verify all dependencies are injected
        self.assertEqual(self.service.answer_repo, self.mock_answer_repo)
        self.assertEqual(self.service.submission_repo, self.mock_submission_repo)
        self.assertEqual(self.service.question_repo, self.mock_question_repo)
        self.assertEqual(self.service.choice_repo, self.mock_choice_repo)
        self.assertEqual(self.service.storage, self.mock_storage)


if __name__ == '__main__':
    unittest.main()
