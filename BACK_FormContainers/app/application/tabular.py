from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from dataclasses import replace

from app.application.commands import (
    AddTableRowCommand, UpdateTableRowCommand, DeleteTableRowCommand,
    TableRowResult, TableCellInput
)
from app.domain.entities import Answer as DAnswer
from app.domain.repositories import (
    AnswerRepository, SubmissionRepository, QuestionRepository,
    ChoiceRepository, ActorRepository
)
from app.domain.ports import FileStorage
from app.domain.exceptions import (
    EntityNotFoundError, BusinessRuleViolationError, ValidationError
)

ROW_META_KEY = "row_index"
TABLE_META_KEY = "table_kind"  # opcional para distinguir tipos de tabla
TABLE_KIND_DEFAULT = "tabular"

class TabularFormService:
    """
    Servicio reusable para manejar formularios en formato tabla (grid).
    No crea tablas nuevas: aprovecha Answer.meta[row_index] para agrupar filas.
    """

    def __init__(
        self,
        *,
        answer_repo: AnswerRepository,
        submission_repo: SubmissionRepository,
        question_repo: QuestionRepository,
        choice_repo: ChoiceRepository,
        actor_repo: ActorRepository,
        storage: FileStorage,
    ):
        self.answer_repo = answer_repo
        self.submission_repo = submission_repo
        self.question_repo = question_repo
        self.choice_repo = choice_repo
        self.actor_repo = actor_repo
        self.storage = storage

    # ----------------- API pública ----------------- #
    def add_row(self, cmd: AddTableRowCommand) -> TableRowResult:
        submission = self._get_submission(cmd.submission_id)
        # calcular row_index si no viene
        row_index = cmd.row_index if cmd.row_index is not None else self._next_row_index(submission.id)
        return self._save_row(submission.id, row_index, cmd.cells, mode="create")

    def update_row(self, cmd: UpdateTableRowCommand) -> TableRowResult:
        submission = self._get_submission(cmd.submission_id)
        self._ensure_row_exists(submission.id, cmd.row_index)
        return self._save_row(submission.id, cmd.row_index, cmd.cells, mode="update")

    def delete_row(self, cmd: DeleteTableRowCommand) -> None:
        submission = self._get_submission(cmd.submission_id)
        # Eliminar todas las Answer que tengan meta[row_index] = cmd.row_index
        answers = self.answer_repo.list_by_submission(submission.id)
        to_delete = [a for a in answers if (a.meta or {}).get(ROW_META_KEY) == cmd.row_index]
        for a in to_delete:
            self.answer_repo.delete(a.id)

    def list_rows(self, submission_id: UUID) -> List[TableRowResult]:
        submission = self._get_submission(submission_id)
        answers = self.answer_repo.list_by_submission(submission.id)
        # agrupar por row_index
        grouped: Dict[int, List[DAnswer]] = {}
        for a in answers:
            ri = (a.meta or {}).get(ROW_META_KEY)
            if ri is None:
                continue
            grouped.setdefault(ri, []).append(a)

        results: List[TableRowResult] = []
        for ri, items in sorted(grouped.items()):
            results.append(TableRowResult(
                submission_id=submission.id,
                row_index=ri,
                values=self._answers_to_row_values(items)
            ))
        return results

    # ----------------- helpers internos ----------------- #
    def _get_submission(self, submission_id: UUID):
        submission = self.submission_repo.get(submission_id)
        if not submission:
            raise EntityNotFoundError(
                message="Submission no encontrada.",
                entity_type="Submission",
                entity_id=str(submission_id)
            )
        return submission

    def _next_row_index(self, submission_id: UUID) -> int:
        answers = self.answer_repo.list_by_submission(submission_id)
        existing = [int((a.meta or {}).get(ROW_META_KEY)) for a in answers if (a.meta or {}).get(ROW_META_KEY) is not None]
        return (max(existing) + 1) if existing else 1

    def _ensure_row_exists(self, submission_id: UUID, row_index: int) -> None:
        answers = self.answer_repo.list_by_submission(submission_id)
        ok = any((a.meta or {}).get(ROW_META_KEY) == row_index for a in answers)
        if not ok:
            raise EntityNotFoundError(
                message="La fila indicada no existe.",
                entity_type="TableRow",
                entity_id=f"{submission_id}#{row_index}"
            )

    def _save_row(self, submission_id: UUID, row_index: int, cells: List[TableCellInput], *, mode: str) -> TableRowResult:
        if not cells:
            raise ValidationError(message="Debes enviar al menos una celda.", field="cells")

        # Limpiar respuestas previas de la misma fila para las mismas preguntas (modo update)
        if mode == "update":
            existing = self.answer_repo.list_by_submission(submission_id)
            for a in existing:
                if (a.meta or {}).get(ROW_META_KEY) == row_index:
                    # si esta pregunta se está reenviando en cells, se borra
                    if any(str(c.question_id) == str(a.question_id) for c in cells):
                        self.answer_repo.delete(a.id)

        # Procesar celdas
        saved: List[DAnswer] = []
        for c in cells:
            q = self.question_repo.get(c.question_id)
            if not q:
                raise EntityNotFoundError(message="Pregunta no encontrada.", entity_type="Question", entity_id=str(c.question_id))

            qtype = (getattr(q, "type", "") or "").lower()
            tag   = (getattr(q, "semantic_tag", "") or "").lower()
            fmode = (getattr(q, "file_mode", "") or "").lower()

            # Validaciones por tipo/semántica
            if tag in {"proveedor", "transportista", "receptor"}:
                if not c.actor_id:
                    raise ValidationError(message=f"Debe enviarse actor_id para la columna '{tag}'.", field="actor_id")
                if not self.actor_repo.get(c.actor_id):
                    raise BusinessRuleViolationError(message="El actor no existe o está inactivo.", rule_name="actor_must_exist")
                # En columnas de actor, NO admitimos texto libre
                answer_text = None
                extra_meta = {"actor_id": str(c.actor_id)}
            else:
                answer_text = (c.answer_text or "").strip() if c.answer_text else None
                extra_meta = {}

            # Archivos en columnas tipo file
            upload = None
            if qtype == "file":
                upload = c.upload
                if upload is None and fmode in {"image_ocr", "ocr_only"}:
                    # permitimos file opcional; si no hay, no guardamos celda
                    pass

            # Persistir archivo si aplica
            saved_path: Optional[str] = None
            if upload is not None:
                saved_path = self.storage.save(folder=f"submissions/{submission_id}", file_obj=upload)

            # Crear entidad Answer con meta de fila + tabla
            meta = {
                ROW_META_KEY: row_index,
                TABLE_META_KEY: TABLE_KIND_DEFAULT,
                **extra_meta
            }

            entity = DAnswer.create_new(
                submission_id=submission_id,
                question_id=q.id,
                user_id=None,
                answer_text=answer_text,
                answer_choice_id=c.answer_choice_id,
                answer_file_path=saved_path,
                ocr_meta=None,
                meta=meta,
            )
            saved.append(self.answer_repo.save(entity))

        return TableRowResult(
            submission_id=submission_id,
            row_index=row_index,
            values=self._answers_to_row_values(saved)
        )

    def _answers_to_row_values(self, answers: List[DAnswer]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for a in answers:
            cell: Dict[str, Any] = {
                "answer_text": a.answer_text,
                "answer_choice_id": a.answer_choice_id,
                "answer_file_path": a.answer_file_path,
            }
            meta = a.meta or {}
            if "actor_id" in meta:
                cell["actor_id"] = meta["actor_id"]
            out[str(a.question_id)] = cell
        return out
