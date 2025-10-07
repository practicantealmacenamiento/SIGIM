from __future__ import annotations
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.application.commands import (
    AddTableRowCommand,
    UpdateTableRowCommand,
    DeleteTableRowCommand,
    TableRowResult,
    TableCellInput,
)
from app.domain.entities import Answer as DAnswer
from app.domain.repositories import (
    AnswerRepository,
    SubmissionRepository,
    QuestionRepository,
    ChoiceRepository,
    ActorRepository,
)
from app.domain.ports import FileStorage
from app.domain.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
    ValidationError,
)

# Metadatos usados para identificar filas/tabla en Answer.meta
TABLE_ID_KEY = "table_id"
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
    def add_row(self, cmd: AddTableRowCommand, table_id: Optional[str] = None) -> TableRowResult:
        submission = self._get_submission(cmd.submission_id)
        row_index = cmd.row_index if cmd.row_index is not None else self._next_row_index(submission.id, table_id)
        return self._save_row(
            submission.id,
            row_index,
            cmd.cells,
            mode="create",
            table_id=table_id,
        )

    def update_row(self, cmd: UpdateTableRowCommand, table_id: Optional[str] = None) -> TableRowResult:
        submission = self._get_submission(cmd.submission_id)
        self._ensure_row_exists(submission.id, cmd.row_index, table_id=table_id)
        return self._save_row(
            submission.id,
            cmd.row_index,
            cmd.cells,
            mode="update",
            table_id=table_id,
        )

    def delete_row(self, cmd: DeleteTableRowCommand, table_id: Optional[str] = None) -> None:
        submission = self._get_submission(cmd.submission_id)
        answers = self.answer_repo.list_by_submission(submission.id)
        to_delete: List[DAnswer] = []
        for a in answers:
            m = a.meta or {}
            if m.get(ROW_META_KEY) == cmd.row_index:
                # Si table_id es None, elimina las filas que no tengan table_id (o lo tengan None).
                # Si viene table_id, elimina sólo las de esa tabla.
                if (table_id is None and m.get(TABLE_ID_KEY) is None) or (m.get(TABLE_ID_KEY) == table_id):
                    to_delete.append(a)
        for a in to_delete:
            self.answer_repo.delete(a.id)

    def list_rows(self, submission_id: UUID, table_id: Optional[str] = None) -> List[TableRowResult]:
        submission = self._get_submission(submission_id)
        answers = self.answer_repo.list_by_submission(submission.id)
        grouped: Dict[int, List[DAnswer]] = {}
        for a in answers:
            m = a.meta or {}
            # Filtrar por tabla si se especifica
            if table_id is not None and m.get(TABLE_ID_KEY) != table_id:
                continue
            ri = m.get(ROW_META_KEY)
            if ri is None:
                continue
            grouped.setdefault(int(ri), []).append(a)

        results: List[TableRowResult] = []
        for ri, items in sorted(grouped.items()):
            results.append(
                TableRowResult(
                    submission_id=submission.id,
                    row_index=ri,
                    values=self._answers_to_row_values(items),
                )
            )
        return results

    # ----------------- helpers internos ----------------- #
    def _get_submission(self, submission_id: UUID):
        submission = self.submission_repo.get(submission_id)
        if not submission:
            raise EntityNotFoundError(
                message="Submission no encontrada.",
                entity_type="Submission",
                entity_id=str(submission_id),
            )
        return submission

    def _next_row_index(self, submission_id: UUID, table_id: Optional[str]) -> int:
        answers = self.answer_repo.list_by_submission(submission_id)
        existing = [
            int((a.meta or {}).get(ROW_META_KEY))
            for a in answers
            if (a.meta or {}).get(ROW_META_KEY) is not None
            and (a.meta or {}).get(TABLE_ID_KEY) == table_id
        ]
        return (max(existing) + 1) if existing else 1

    def _ensure_row_exists(self, submission_id: UUID, row_index: int, *, table_id: Optional[str]) -> None:
        answers = self.answer_repo.list_by_submission(submission_id)
        ok = any(
            (a.meta or {}).get(ROW_META_KEY) == row_index
            and ((table_id is None and (a.meta or {}).get(TABLE_ID_KEY) is None) or (a.meta or {}).get(TABLE_ID_KEY) == table_id)
            for a in answers
        )
        if not ok:
            raise EntityNotFoundError(
                message="La fila indicada no existe.",
                entity_type="TableRow",
                entity_id=f"{submission_id}#{table_id or ''}#{row_index}",
            )

    def _save_row(
        self,
        submission_id: UUID,
        row_index: int,
        cells: List[TableCellInput],
        *,
        mode: str,  # "create" | "update"
        table_id: Optional[str] = None,
    ) -> TableRowResult:
        """
        Crea/actualiza todas las celdas de una fila.
        - En modo update, elimina previamente las respuestas de la misma fila/tabla para
          las preguntas que se están reenviando.
        - Nunca crea respuestas "vacías" (sin texto, sin opción y sin archivo).
        - En columnas con semántica de actor, además de guardar actor_id en meta,
          setea answer_text con un display no vacío para cumplir invariantes.
        """
        if not cells:
            raise ValidationError(message="Debes enviar al menos una celda.", field="cells")

        # Limpiar respuestas previas de la misma fila/tabla para las mismas preguntas (modo update)
        if mode == "update":
            existing = self.answer_repo.list_by_submission(submission_id)
            for a in existing:
                m = a.meta or {}
                if m.get(ROW_META_KEY) == row_index and (
                    (table_id is None and m.get(TABLE_ID_KEY) is None) or (m.get(TABLE_ID_KEY) == table_id)
                ):
                    # Si esta pregunta se está reenviando en cells, se borra
                    if any(str(c.question_id) == str(a.question_id) for c in cells):
                        self.answer_repo.delete(a.id)

        # Procesar celdas
        saved: List[DAnswer] = []
        for c in cells:
            q = self.question_repo.get(c.question_id)
            if not q:
                raise EntityNotFoundError(
                    message="Pregunta no encontrada.",
                    entity_type="Question",
                    entity_id=str(c.question_id),
                )

            qtype = (getattr(q, "type", "") or "").lower()
            tag = (getattr(q, "semantic_tag", "") or "").lower()
            fmode = (getattr(q, "file_mode", "") or "").lower()

            # --- Validaciones por tipo/semántica ---
            answer_text: Optional[str] = None
            extra_meta: Dict[str, Any] = {}

            if tag in {"proveedor", "transportista", "receptor"}:
                # Columnas mapeadas a un Actor: requerimos actor_id y guardamos display en answer_text
                if not c.actor_id:
                    raise ValidationError(message=f"Debe enviarse actor_id para la columna '{tag}'.", field="actor_id")
                actor = self.actor_repo.get(c.actor_id)
                if not actor:
                    raise BusinessRuleViolationError(
                        message="El actor no existe o está inactivo.",
                        rule_name="actor_must_exist",
                    )

                # Cumplir invariante de Answer con un texto no vacío
                display = (
                    getattr(actor, "nombre", None)
                    or getattr(actor, "razon_social", None)
                    or getattr(actor, "full_name", None)
                    or str(actor.id)
                )
                answer_text = str(display).strip() or str(actor.id)
                extra_meta = {"actor_id": str(c.actor_id)}
            else:
                # Texto normal (si viene)
                answer_text = (c.answer_text or "").strip() if c.answer_text else None
                extra_meta = {}

            # --- Archivos ---
            upload = None
            if qtype == "file":
                upload = c.upload

            # Si la celda resultaría totalmente vacía (sin texto, sin opción y sin archivo), saltar
            is_empty_cell = (answer_text is None or answer_text == "") and (c.answer_choice_id is None) and (upload is None)

            # En modos OCR, permitir omitir archivo, pero si además no hay texto/opción, no crear Answer
            if is_empty_cell:
                # No persistir respuestas vacías (evita violar el invariante de Answer)
                continue

            # Persistir archivo si aplica
            saved_path: Optional[str] = None
            if upload is not None:
                saved_path = self.storage.save(folder=f"submissions/{submission_id}", file_obj=upload)

            # Crear entidad Answer con meta de fila + tabla
            meta = {
                ROW_META_KEY: row_index,
                TABLE_META_KEY: TABLE_KIND_DEFAULT,
                **extra_meta,
            }
            if table_id is not None:
                meta[TABLE_ID_KEY] = table_id

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
            values=self._answers_to_row_values(saved),
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
