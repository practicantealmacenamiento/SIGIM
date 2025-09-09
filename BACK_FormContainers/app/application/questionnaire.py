from __future__ import annotations

from typing import Optional
from uuid import UUID
from dataclasses import replace

from app.application.commands import SaveAndAdvanceCommand, SaveAndAdvanceResult
from app.application.exceptions import ValidationError, DomainError
from app.domain.entities import Answer as DAnswer
from app.domain.repositories import (
    AnswerRepository,
    SubmissionRepository,
    QuestionRepository,
    ChoiceRepository,
)
from app.domain.ports import FileStorage


class QuestionnaireService:
    """
    Caso de uso principal del flujo de formulario (Guardar y Avanzar).

    Reglas de adjuntos (en capa de aplicación):
      - type == "file"  -> acepta archivos.
      - file_mode in {"image_ocr", "ocr_only"} -> máx 1 archivo.
      - otros/None -> máx 2 archivos (alineado a tu UI).
    """

    def __init__(
        self,
        answer_repo: AnswerRepository,
        submission_repo: SubmissionRepository,
        question_repo: QuestionRepository,
        choice_repo: ChoiceRepository,
        storage: FileStorage,
    ):
        self.answer_repo = answer_repo
        self.submission_repo = submission_repo
        self.question_repo = question_repo
        self.choice_repo = choice_repo
        self.storage = storage

    def save_and_advance(self, cmd: SaveAndAdvanceCommand) -> SaveAndAdvanceResult:
        # 1) Cargar aggregate raíz
        submission = self.submission_repo.get(cmd.submission_id)
        if not submission:
            raise DomainError("Submission no encontrada.")

        question = self.question_repo.get(cmd.question_id)
        if not question:
            raise DomainError("Pregunta no encontrada.")

        qtype = (getattr(question, "type", "") or "").lower()
        fmode = (getattr(question, "file_mode", "") or "").lower()

        # 2) Validaciones del payload
        has_text = bool((cmd.answer_text or "").strip())
        has_choice = cmd.answer_choice_id is not None
        has_uploads = bool(cmd.uploads)

        choice = None
        if has_choice:
            choice = self.choice_repo.get(cmd.answer_choice_id)
            if not choice:
                raise ValidationError("La opción indicada no existe.")
            # Validar pertenencia
            qid = getattr(choice, "question_id", None) or getattr(getattr(choice, "question", None), "id", None)
            if qid and str(qid) != str(question.id):
                raise ValidationError("La opción no pertenece a la pregunta indicada.")

        # 3) Reglas de adjuntos
        max_files = 0
        if qtype == "file":
            max_files = 1 if fmode in {"image_ocr", "ocr_only"} else 2

        if has_uploads and max_files == 0:
            raise ValidationError("Esta pregunta no acepta archivos adjuntos.")

        if has_uploads and len(cmd.uploads) > max_files:
            uploads_clamped = (cmd.uploads or [])[:max_files]
            cmd = replace(cmd, uploads=uploads_clamped)

        # 4) Requeridos
        if getattr(question, "required", False):
            if not (has_text or has_choice or has_uploads):
                raise ValidationError("La pregunta es obligatoria.")

        # 5) Truncar futuras respuestas si aplica
        if cmd.force_truncate_future:
            self.answer_repo.delete_after_question(submission_id=submission.id, question_id=question.id)

        # 6) Limpiar respuestas previas de la misma pregunta
        self.answer_repo.clear_for_question(submission_id=submission.id, question_id=question.id)

        # 7) Persistir archivo (si hay)
        saved_path: Optional[str] = None
        if has_uploads:
            uf = cmd.uploads[0]
            saved_path = self.storage.save(folder=f"submissions/{submission.id}", file_obj=uf)

        # 8) Construir entidad (campo correcto: answer_text)
        entity = DAnswer.create_new(
            submission_id=submission.id,
            question_id=question.id,
            user_id=cmd.user_id,
            answer_text=cmd.answer_text,
            answer_choice_id=cmd.answer_choice_id,
            answer_file_path=saved_path,
            ocr_meta=None,
            meta=None,
        )
        saved = self.answer_repo.save(entity)

        # 9) Resolver siguiente pregunta (con ramificación si hay choice.branch_to)
        next_qid: Optional[UUID] = None
        # a) si hubo choice y define branch_to, úsalo
        if choice:
            branch = getattr(choice, "branch_to", None) or getattr(choice, "branch_to_id", None)
            if branch:
                next_qid = branch

        # b) si no hay branch, resolver por orden
        if next_qid is None:
            try:
                next_qid = self.question_repo.next_in_questionnaire(question.id)
            except Exception:
                try:
                    nxt = self.question_repo.find_next_by_order(
                        questionnaire_id=getattr(question, "questionnaire_id", None),
                        order=getattr(question, "order", 0),
                    )
                    next_qid = getattr(nxt, "id", None) if nxt else None
                except Exception:
                    next_qid = None

        is_finished = next_qid is None

        return SaveAndAdvanceResult(
            saved_answer=saved,
            next_question_id=next_qid,
            is_finished=is_finished,
            derived_updates={},
            warnings=[],
        )