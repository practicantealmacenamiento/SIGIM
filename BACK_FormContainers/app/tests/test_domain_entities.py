"""
Pruebas unitarias para entidades de dominio.

Estas pruebas verifican:
1. Reglas de negocio y validaciones de entidades
2. Invariantes de dominio
3. Comportamiento de métodos de entidades
4. Que las entidades no tengan dependencias externas
"""
import unittest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from typing import Dict, Any

from app.domain.entities import Answer, Submission, Question, Choice, Questionnaire
from app.domain.exceptions import (
    ValidationError, 
    InvariantViolationError, 
    BusinessRuleViolationError
)


class TestChoice(unittest.TestCase):
    """Pruebas para la entidad Choice."""

    def test_create_valid_choice(self):
        """Debe crear una opción válida."""
        choice_id = uuid4()
        choice = Choice(
            id=choice_id,
            text="Opción válida",
            branch_to=None
        )
        
        self.assertEqual(choice.id, choice_id)
        self.assertEqual(choice.text, "Opción válida")
        self.assertIsNone(choice.branch_to)
        self.assertFalse(choice.has_branch())

    def test_choice_with_branch(self):
        """Debe crear una opción con ramificación."""
        choice_id = uuid4()
        branch_id = uuid4()
        choice = Choice(
            id=choice_id,
            text="Opción con rama",
            branch_to=branch_id
        )
        
        self.assertTrue(choice.has_branch())
        self.assertEqual(choice.branch_to, branch_id)

    def test_choice_text_normalization(self):
        """Debe normalizar el texto de la opción."""
        choice = Choice(
            id=uuid4(),
            text="  Texto con espacios  ",
            branch_to=None
        )
        
        self.assertEqual(choice.text, "Texto con espacios")

    def test_empty_text_raises_validation_error(self):
        """Debe lanzar ValidationError si el texto está vacío."""
        with self.assertRaises(ValidationError) as context:
            Choice(
                id=uuid4(),
                text="",
                branch_to=None
            )
        
        self.assertIn("texto de la opción no puede estar vacío", str(context.exception))

    def test_whitespace_only_text_raises_validation_error(self):
        """Debe lanzar ValidationError si el texto solo contiene espacios."""
        with self.assertRaises(ValidationError) as context:
            Choice(
                id=uuid4(),
                text="   ",
                branch_to=None
            )
        
        self.assertIn("texto de la opción no puede estar vacío", str(context.exception))

    def test_get_display_text(self):
        """Debe retornar el texto para mostrar."""
        choice = Choice(
            id=uuid4(),
            text="Texto de prueba",
            branch_to=None
        )
        
        self.assertEqual(choice.get_display_text(), "Texto de prueba")


class TestQuestion(unittest.TestCase):
    """Pruebas para la entidad Question."""

    def test_create_valid_text_question(self):
        """Debe crear una pregunta de texto válida."""
        question_id = uuid4()
        question = Question(
            id=question_id,
            text="¿Cuál es tu nombre?",
            type="text",
            required=True,
            order=1,
            choices=None,
            semantic_tag=None,
            file_mode=None
        )
        
        self.assertEqual(question.id, question_id)
        self.assertEqual(question.text, "¿Cuál es tu nombre?")
        self.assertEqual(question.type, "text")
        self.assertTrue(question.required)
        self.assertEqual(question.order, 1)
        self.assertTrue(question.is_text_question())
        self.assertFalse(question.is_choice_question())
        self.assertFalse(question.is_file_question())

    def test_create_valid_choice_question(self):
        """Debe crear una pregunta de opción múltiple válida."""
        choice1 = Choice(id=uuid4(), text="Opción 1")
        choice2 = Choice(id=uuid4(), text="Opción 2")
        
        question = Question(
            id=uuid4(),
            text="¿Cuál prefieres?",
            type="choice",
            required=True,
            order=1,
            choices=[choice1, choice2]
        )
        
        self.assertTrue(question.is_choice_question())
        self.assertEqual(len(question.choices), 2)
        self.assertEqual(question.get_choices_count(), 2)

    def test_create_valid_file_question(self):
        """Debe crear una pregunta de archivo válida."""
        question = Question(
            id=uuid4(),
            text="Sube tu documento",
            type="file",
            required=True,
            order=1,
            file_mode="image_ocr"
        )
        
        self.assertTrue(question.is_file_question())
        self.assertTrue(question.has_ocr_capability())

    def test_invalid_question_type_raises_error(self):
        """Debe lanzar ValidationError para tipo de pregunta inválido."""
        with self.assertRaises(ValidationError) as context:
            Question(
                id=uuid4(),
                text="Pregunta inválida",
                type="invalid_type",
                required=True,
                order=1
            )
        
        self.assertIn("Tipo de pregunta inválido", str(context.exception))

    def test_empty_text_raises_validation_error(self):
        """Debe lanzar ValidationError si el texto está vacío."""
        with self.assertRaises(ValidationError) as context:
            Question(
                id=uuid4(),
                text="",
                type="text",
                required=True,
                order=1
            )
        
        self.assertIn("texto de la pregunta no puede estar vacío", str(context.exception))

    def test_negative_order_raises_validation_error(self):
        """Debe lanzar ValidationError si el orden es negativo."""
        with self.assertRaises(ValidationError) as context:
            Question(
                id=uuid4(),
                text="Pregunta válida",
                type="text",
                required=True,
                order=-1
            )
        
        self.assertIn("orden de la pregunta debe ser un número positivo", str(context.exception))

    def test_choice_question_without_choices_raises_error(self):
        """Debe lanzar ValidationError si pregunta choice no tiene opciones."""
        with self.assertRaises(ValidationError) as context:
            Question(
                id=uuid4(),
                text="¿Cuál prefieres?",
                type="choice",
                required=True,
                order=1,
                choices=None
            )
        
        self.assertIn("preguntas de tipo 'choice' deben tener al menos una opción", str(context.exception))

    def test_non_choice_question_with_choices_raises_error(self):
        """Debe lanzar ValidationError si pregunta no-choice tiene opciones."""
        choice = Choice(id=uuid4(), text="Opción")
        
        with self.assertRaises(ValidationError) as context:
            Question(
                id=uuid4(),
                text="Pregunta de texto",
                type="text",
                required=True,
                order=1,
                choices=[choice]
            )
        
        self.assertIn("preguntas de tipo 'text' no pueden tener opciones", str(context.exception))

    def test_get_choice_by_id(self):
        """Debe encontrar una opción por su ID."""
        choice1_id = uuid4()
        choice2_id = uuid4()
        choice1 = Choice(id=choice1_id, text="Opción 1")
        choice2 = Choice(id=choice2_id, text="Opción 2")
        
        question = Question(
            id=uuid4(),
            text="¿Cuál prefieres?",
            type="choice",
            required=True,
            order=1,
            choices=[choice1, choice2]
        )
        
        found_choice = question.get_choice_by_id(choice1_id)
        self.assertIsNotNone(found_choice)
        self.assertEqual(found_choice.id, choice1_id)
        
        not_found = question.get_choice_by_id(uuid4())
        self.assertIsNone(not_found)

    def test_validate_answer_choice(self):
        """Debe validar si un choice_id es válido para la pregunta."""
        choice_id = uuid4()
        choice = Choice(id=choice_id, text="Opción válida")
        
        question = Question(
            id=uuid4(),
            text="¿Cuál prefieres?",
            type="choice",
            required=True,
            order=1,
            choices=[choice]
        )
        
        self.assertTrue(question.validate_answer_choice(choice_id))
        self.assertFalse(question.validate_answer_choice(uuid4()))


class TestQuestionnaire(unittest.TestCase):
    """Pruebas para la entidad Questionnaire."""

    def test_create_valid_questionnaire(self):
        """Debe crear un cuestionario válido."""
        question = Question(
            id=uuid4(),
            text="Pregunta de prueba",
            type="text",
            required=True,
            order=1
        )
        
        questionnaire = Questionnaire(
            id=uuid4(),
            title="Cuestionario de prueba",
            version="1.0",
            timezone="UTC",
            questions=[question]
        )
        
        self.assertEqual(questionnaire.title, "Cuestionario de prueba")
        self.assertEqual(len(questionnaire.questions), 1)

    def test_empty_title_raises_validation_error(self):
        """Debe lanzar ValidationError si el título está vacío."""
        question = Question(
            id=uuid4(),
            text="Pregunta de prueba",
            type="text",
            required=True,
            order=1
        )
        
        with self.assertRaises(ValidationError) as context:
            Questionnaire(
                id=uuid4(),
                title="",
                version="1.0",
                timezone="UTC",
                questions=[question]
            )
        
        self.assertIn("título del cuestionario no puede estar vacío", str(context.exception))

    def test_no_questions_raises_invariant_violation(self):
        """Debe lanzar InvariantViolationError si no hay preguntas."""
        with self.assertRaises(InvariantViolationError) as context:
            Questionnaire(
                id=uuid4(),
                title="Cuestionario sin preguntas",
                version="1.0",
                timezone="UTC",
                questions=[]
            )
        
        self.assertIn("cuestionario debe tener al menos una pregunta", str(context.exception))

    def test_get_question_by_id(self):
        """Debe encontrar una pregunta por su ID."""
        question_id = uuid4()
        question = Question(
            id=question_id,
            text="Pregunta de prueba",
            type="text",
            required=True,
            order=1
        )
        
        questionnaire = Questionnaire(
            id=uuid4(),
            title="Cuestionario de prueba",
            version="1.0",
            timezone="UTC",
            questions=[question]
        )
        
        found_question = questionnaire.get_question_by_id(question_id)
        self.assertIsNotNone(found_question)
        self.assertEqual(found_question.id, question_id)

    def test_get_questions_by_order(self):
        """Debe retornar preguntas ordenadas por el campo order."""
        question1 = Question(id=uuid4(), text="Pregunta 3", type="text", required=True, order=3)
        question2 = Question(id=uuid4(), text="Pregunta 1", type="text", required=True, order=1)
        question3 = Question(id=uuid4(), text="Pregunta 2", type="text", required=True, order=2)
        
        questionnaire = Questionnaire(
            id=uuid4(),
            title="Cuestionario de prueba",
            version="1.0",
            timezone="UTC",
            questions=[question1, question2, question3]
        )
        
        ordered_questions = questionnaire.get_questions_by_order()
        self.assertEqual(len(ordered_questions), 3)
        self.assertEqual(ordered_questions[0].order, 1)
        self.assertEqual(ordered_questions[1].order, 2)
        self.assertEqual(ordered_questions[2].order, 3)


class TestSubmission(unittest.TestCase):
    """Pruebas para la entidad Submission."""

    def test_create_new_submission(self):
        """Debe crear un nuevo submission."""
        questionnaire_id = uuid4()
        regulador_id = uuid4()
        
        submission = Submission.create_new(
            questionnaire_id=questionnaire_id,
            tipo_fase="entrada",
            regulador_id=regulador_id,
            placa_vehiculo="ABC123"
        )
        
        self.assertEqual(submission.questionnaire_id, questionnaire_id)
        self.assertEqual(submission.tipo_fase, "entrada")
        self.assertEqual(submission.regulador_id, regulador_id)
        self.assertEqual(submission.placa_vehiculo, "ABC123")
        self.assertFalse(submission.finalizado)
        self.assertIsNone(submission.fecha_cierre)
        self.assertTrue(submission.can_be_modified())

    def test_invalid_tipo_fase_raises_validation_error(self):
        """Debe lanzar ValidationError para tipo_fase inválido."""
        with self.assertRaises(ValidationError) as context:
            Submission.create_new(
                questionnaire_id=uuid4(),
                tipo_fase="invalid_type",
            )
        
        self.assertIn("tipo de fase debe ser 'entrada' o 'salida'", str(context.exception))

    def test_finalize_submission(self):
        """Debe finalizar un submission correctamente."""
        submission = Submission.create_new(
            questionnaire_id=uuid4(),
            tipo_fase="entrada"
        )
        
        finalized = submission.finalize()
        
        self.assertTrue(finalized.finalizado)
        self.assertIsNotNone(finalized.fecha_cierre)
        self.assertFalse(finalized.can_be_modified())
        self.assertTrue(finalized.is_finalized())

    def test_finalize_already_finalized_raises_error(self):
        """Debe lanzar BusinessRuleViolationError si ya está finalizado."""
        submission = Submission.create_new(
            questionnaire_id=uuid4(),
            tipo_fase="entrada"
        )
        
        finalized = submission.finalize()
        
        with self.assertRaises(BusinessRuleViolationError) as context:
            finalized.finalize()
        
        self.assertIn("submission ya está finalizado", str(context.exception))

    def test_finalized_submission_invariants(self):
        """Debe validar invariantes de submission finalizado."""
        # Crear submission finalizado manualmente (violando invariante)
        with self.assertRaises(InvariantViolationError) as context:
            Submission(
                id=uuid4(),
                questionnaire_id=uuid4(),
                tipo_fase="entrada",
                finalizado=True,
                fecha_cierre=None  # Violación: finalizado sin fecha de cierre
            )
        
        self.assertIn("submission finalizado debe tener fecha de cierre", str(context.exception))

    def test_unfinalized_submission_with_close_date_raises_error(self):
        """Debe lanzar InvariantViolationError si no finalizado tiene fecha de cierre."""
        with self.assertRaises(InvariantViolationError) as context:
            Submission(
                id=uuid4(),
                questionnaire_id=uuid4(),
                tipo_fase="entrada",
                finalizado=False,
                fecha_cierre=datetime.now(timezone.utc)  # Violación
            )
        
        self.assertIn("submission no finalizado no puede tener fecha de cierre", str(context.exception))


class TestAnswer(unittest.TestCase):
    """Pruebas para la entidad Answer."""

    def test_create_text_answer(self):
        """Debe crear una respuesta de texto válida."""
        submission_id = uuid4()
        question_id = uuid4()
        
        answer = Answer.create_new(
            submission_id=submission_id,
            question_id=question_id,
            answer_text="Respuesta de texto"
        )
        
        self.assertEqual(answer.submission_id, submission_id)
        self.assertEqual(answer.question_id, question_id)
        self.assertEqual(answer.answer_text, "Respuesta de texto")
        self.assertTrue(answer.is_text_answer())
        self.assertFalse(answer.is_choice_answer())
        self.assertFalse(answer.is_file_answer())
        self.assertTrue(answer.has_content())

    def test_create_choice_answer(self):
        """Debe crear una respuesta de opción válida."""
        choice_id = uuid4()
        
        answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_choice_id=choice_id
        )
        
        self.assertEqual(answer.answer_choice_id, choice_id)
        self.assertTrue(answer.is_choice_answer())
        self.assertFalse(answer.is_text_answer())
        self.assertFalse(answer.is_file_answer())

    def test_create_file_answer(self):
        """Debe crear una respuesta de archivo válida."""
        answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_file_path="/path/to/file.jpg"
        )
        
        self.assertEqual(answer.answer_file_path, "/path/to/file.jpg")
        self.assertTrue(answer.is_file_answer())
        self.assertFalse(answer.is_text_answer())
        self.assertFalse(answer.is_choice_answer())

    def test_answer_without_content_raises_invariant_violation(self):
        """Debe lanzar InvariantViolationError si no tiene contenido."""
        with self.assertRaises(InvariantViolationError) as context:
            Answer.create_new(
                submission_id=uuid4(),
                question_id=uuid4()
                # Sin answer_text, answer_choice_id, ni answer_file_path
            )
        
        self.assertIn("respuesta debe contener texto, una opción o un archivo", str(context.exception))

    def test_text_normalization(self):
        """Debe normalizar el texto de la respuesta."""
        answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="  Texto con espacios  "
        )
        
        self.assertEqual(answer.answer_text, "Texto con espacios")

    def test_empty_text_is_normalized_to_none(self):
        """Debe normalizar texto vacío a None."""
        answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="   ",  # Solo espacios
            answer_choice_id=uuid4()  # Necesario para tener contenido
        )
        
        self.assertIsNone(answer.answer_text)

    def test_with_text_immutable_update(self):
        """Debe crear nueva instancia con texto actualizado."""
        original = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="Texto original"
        )
        
        updated = original.with_text("Texto actualizado")
        
        # Original no debe cambiar
        self.assertEqual(original.answer_text, "Texto original")
        # Nueva instancia debe tener el texto actualizado
        self.assertEqual(updated.answer_text, "Texto actualizado")
        # Otros campos deben ser iguales
        self.assertEqual(original.id, updated.id)
        self.assertEqual(original.submission_id, updated.submission_id)

    def test_with_choice_immutable_update(self):
        """Debe crear nueva instancia con opción actualizada."""
        original_choice = uuid4()
        new_choice = uuid4()
        
        original = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_choice_id=original_choice
        )
        
        updated = original.with_choice(new_choice)
        
        self.assertEqual(original.answer_choice_id, original_choice)
        self.assertEqual(updated.answer_choice_id, new_choice)

    def test_with_file_path_immutable_update(self):
        """Debe crear nueva instancia con ruta de archivo actualizada."""
        original = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_file_path="/original/path.jpg"
        )
        
        updated = original.with_file_path("/new/path.jpg")
        
        self.assertEqual(original.answer_file_path, "/original/path.jpg")
        self.assertEqual(updated.answer_file_path, "/new/path.jpg")

    def test_with_ocr_meta_immutable_update(self):
        """Debe crear nueva instancia con metadatos OCR actualizados."""
        original = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="Texto con OCR",
            ocr_meta={"confidence": 0.8}
        )
        
        updated = original.with_ocr_meta({"confidence": 0.9, "language": "es"})
        
        self.assertEqual(original.ocr_meta, {"confidence": 0.8})
        self.assertEqual(updated.ocr_meta, {"confidence": 0.9, "language": "es"})

    def test_has_ocr_data(self):
        """Debe detectar si tiene datos de OCR."""
        answer_without_ocr = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="Texto sin OCR"
        )
        
        answer_with_ocr = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="Texto con OCR",
            ocr_meta={"confidence": 0.9}
        )
        
        self.assertFalse(answer_without_ocr.has_ocr_data())
        self.assertTrue(answer_with_ocr.has_ocr_data())

    def test_get_display_value(self):
        """Debe retornar valor apropiado para mostrar."""
        text_answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_text="Mi respuesta"
        )
        
        choice_answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_choice_id=uuid4()
        )
        
        file_answer = Answer.create_new(
            submission_id=uuid4(),
            question_id=uuid4(),
            answer_file_path="/path/to/file.jpg"
        )
        
        self.assertEqual(text_answer.get_display_value(), "Mi respuesta")
        self.assertIn("Opción:", choice_answer.get_display_value())
        self.assertIn("Archivo:", file_answer.get_display_value())

    def test_rehydrate_from_persistence(self):
        """Debe rehidratar correctamente desde persistencia."""
        answer_id = uuid4()
        submission_id = uuid4()
        question_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        
        answer = Answer.rehydrate(
            id=answer_id,
            submission_id=submission_id,
            question_id=question_id,
            user_id=None,
            answer_text="Texto rehidratado",
            answer_choice_id=None,
            answer_file_path=None,
            ocr_meta={"confidence": 0.95},
            meta={"source": "test"},
            timestamp=timestamp
        )
        
        self.assertEqual(answer.id, answer_id)
        self.assertEqual(answer.submission_id, submission_id)
        self.assertEqual(answer.question_id, question_id)
        self.assertEqual(answer.answer_text, "Texto rehidratado")
        self.assertEqual(answer.ocr_meta, {"confidence": 0.95})
        self.assertEqual(answer.meta, {"source": "test"})
        self.assertEqual(answer.timestamp, timestamp)


if __name__ == '__main__':
    unittest.main()