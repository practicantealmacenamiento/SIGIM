"""
Caso de uso principal del flujo de formulario (Guardar y Avanzar).

Responsabilidades:
- Validar existencia de `Submission` y `Question`.
- Aplicar reglas de adjuntos por tipo de pregunta.
- Guardar respuesta:
    * Rama clásica (texto / choice / 1 archivo) con limpieza selectiva.
    * Rama proveedor (Opción B): merge de filas (sin limpiar la pregunta).
- Resolver la siguiente pregunta (ramas por `branch_to` o navegación lineal).
- Emitir efectos derivados (updates de submission y contadores).

Notas:
- No introduce dependencias de infraestructura; usa puertos/repositorios.
- No mover reglas de dominio aquí; este módulo orquesta casos de uso.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
import json
from dataclasses import replace
from uuid import UUID
from typing import Optional, List, Dict, Any

# ── Application ────────────────────────────────────────────────────────────────
from app.application.commands import SaveAndAdvanceCommand, SaveAndAdvanceResult

# ── Dominio ────────────────────────────────────────────────────────────────────
from app.domain.entities import Answer as DAnswer
from app.domain.exceptions import (
    ValidationError,
    EntityNotFoundError,
    BusinessRuleViolationError,
)
from app.domain.ports.repositories import (
    AnswerRepository,
    SubmissionRepository,
    QuestionRepository,
    ChoiceRepository,
)
from app.domain.ports.external_ports import FileStorage


__all__ = ["QuestionnaireService"]


class QuestionnaireService:
    """
    Servicio de aplicación que implementa el caso de uso “Guardar y Avanzar”.

    Reglas de adjuntos (a nivel aplicación):
      - type == "file"  → acepta archivos.
      - file_mode in {"image_ocr", "ocr_only"} → máx 1 archivo.
      - otros/None → máx 2 archivos (alineado a la UI).

    Opción B (sin campos tabulares en Question):
      - Para PROVEEDOR guardamos N `Answer` (una por proveedor) y **no** limpiamos la pregunta.
      - Merge por clave (nombre + orden_compra) para no duplicar ni pisar históricos
        dentro del mismo submission/pregunta.
    """

    def __init__(
        self,
        *,
        answer_repo: AnswerRepository,
        submission_repo: SubmissionRepository,
        question_repo: QuestionRepository,
        choice_repo: ChoiceRepository,
        storage: FileStorage,
    ) -> None:
        self.answer_repo = answer_repo
        self.submission_repo = submission_repo
        self.question_repo = question_repo
        self.choice_repo = choice_repo
        self.storage = storage

    # ==========================================================================
    #   Utilidades públicas
    # ==========================================================================

    def get_first_question(self, questionnaire_id: UUID):
        """
        Retorna la primera pregunta del cuestionario (según orden natural de repo).

        Raises:
            EntityNotFoundError: si no hay `questionnaire_id` o no tiene preguntas.
        """
        if not questionnaire_id:
            raise EntityNotFoundError(
                message="Debes indicar un questionnaire_id",
                entity_type="Questionnaire",
                entity_id="(none)",
            )

        questions = self.question_repo.list_by_questionnaire(questionnaire_id)
        if not questions:
            raise EntityNotFoundError(
                message="No hay preguntas para este cuestionario.",
                entity_type="Question",
                entity_id=str(questionnaire_id),
            )
        return questions[0]

    # ==========================================================================
    #   Normalizaciones/parse (uso interno)
    # ==========================================================================

    def _normalize_unidad(self, raw: str) -> str:
        """
        Normaliza abreviaturas de unidades para proveedores.
        """
        s = (raw or "").strip().upper()
        if s in {"KG", "KGS", "KILOS", "KILOGRAMOS"}:
            return "KG"
        if s in {"UN", "UND", "UNIDADES", "UNS"}:
            return "UN"
        return ""

    def _parse_proveedor_rows(self, payload: str) -> List[Dict[str, Any]]:
        """
        Espera JSON:
            [{"nombre": str, "estibas": int|null, "orden_compra": str,
              "recipientes": int|null, "unidad": "KG"|"UN"|""}, ...]

        Retorna:
            Lista normalizada y validada (sin duplicados por 'nombre').

        Raises:
            ValidationError: formato inválido o datos inconsistentes.
        """
        try:
            data = json.loads(payload or "[]")
        except Exception:
            raise ValidationError(message="Formato inválido: se esperaba un JSON de proveedores.", field="answer")

        if not isinstance(data, list):
            raise ValidationError(message="Se esperaba una lista de proveedores en JSON.", field="answer")

        out: List[Dict[str, Any]] = []
        seen = set()

        for row in data:
            if not isinstance(row, dict):
                continue

            nombre = str(row.get("nombre", "")).strip()
            if not nombre:
                raise ValidationError(message="Cada proveedor debe incluir 'nombre'.", field="answer")

            key = nombre.lower()
            if key in seen:
                # evita duplicados por nombre en el mismo payload
                continue
            seen.add(key)

            # estibas
            try:
                estibas = row.get("estibas", None)
                estibas = None if estibas in ("", None) else int(estibas)
                if estibas is not None and estibas < 0:
                    raise ValueError()
            except Exception:
                raise ValidationError(message=f"Estibas inválidas para proveedor '{nombre}'.", field="answer")

            # recipientes
            try:
                recip = row.get("recipientes", None)
                recip = None if recip in ("", None) else int(recip)
                if recip is not None and recip < 0:
                    raise ValueError()
            except Exception:
                raise ValidationError(message=f"Recipientes inválidos para proveedor '{nombre}'.", field="answer")

            orden_compra = str(row.get("orden_compra", row.get("oc", "") or "")).strip()
            unidad = self._normalize_unidad(row.get("unidad", ""))

            out.append({
                "nombre": nombre,
                "estibas": estibas,
                "orden_compra": orden_compra,
                "recipientes": recip,
                "unidad": unidad,
            })

        if not out:
            raise ValidationError(message="Agrega al menos un proveedor válido.", field="answer")
        return out

    # ==========================================================================
    #   Caso de uso principal
    # ==========================================================================

    def save_and_advance(self, cmd: SaveAndAdvanceCommand) -> SaveAndAdvanceResult:
        """
        Guarda la respuesta actual y calcula la siguiente pregunta del flujo.

        Reglas clave:
          - “Proveedor” (tag semántico) → rama multi-fila *sin limpiar* la pregunta.
          - Resto de preguntas → limpieza de la misma pregunta (no proveedor) y
            truncado de respuestas futuras (si `force_truncate_future=True`).

        Returns:
            SaveAndAdvanceResult con la respuesta persistida, el id de la
            siguiente pregunta (o None), `is_finished` y metadatos derivados.
        """
        # 1) Cargar aggregate y validar existencia
        submission = self.submission_repo.get(cmd.submission_id)
        if not submission:
            raise EntityNotFoundError(
                message="Submission no encontrada.",
                entity_type="Submission",
                entity_id=str(cmd.submission_id),
            )

        question = self.question_repo.get(cmd.question_id)
        if not question:
            raise EntityNotFoundError(
                message="Pregunta no encontrada.",
                entity_type="Question",
                entity_id=str(cmd.question_id),
            )

        # Atributos del comando (no asumimos presencia)
        answer_text = getattr(cmd, "answer_text", None)
        answer_choice_id = getattr(cmd, "answer_choice_id", None)
        uploads = getattr(cmd, "uploads", None)
        user_id = getattr(cmd, "user_id", None)
        actor_id = getattr(cmd, "actor_id", None)
        force_truncate_future = getattr(cmd, "force_truncate_future", False)

        # Metadatos de la pregunta
        qtype = (getattr(question, "type", "") or "").lower()
        fmode = (getattr(question, "file_mode", "") or "").lower()
        tag = (getattr(question, "semantic_tag", "") or "").lower()

        has_text = bool((answer_text or "").strip())
        has_choice = answer_choice_id is not None
        has_uploads = bool(uploads)

        # Validación de choice
        choice = None
        if has_choice:
            choice = self.choice_repo.get(answer_choice_id)
            if not choice:
                raise EntityNotFoundError(
                    message="La opción indicada no existe.",
                    entity_type="Choice",
                    entity_id=str(answer_choice_id),
                )
            # La opción debe pertenecer a la pregunta
            qid = getattr(choice, "question_id", None) or getattr(getattr(choice, "question", None), "id", None)
            if qid and str(qid) != str(question.id):
                raise BusinessRuleViolationError(
                    message="La opción no pertenece a la pregunta indicada.",
                    rule_name="choice_belongs_to_question",
                )

        # 2) Reglas de archivos
        max_files = 0
        if qtype == "file":
            max_files = 1 if fmode in {"image_ocr", "ocr_only"} else 2
        if has_uploads and max_files == 0:
            raise BusinessRuleViolationError(
                message="Esta pregunta no acepta archivos adjuntos.",
                rule_name="question_file_upload_not_allowed",
            )
        if has_uploads and len(uploads) > max_files:
            uploads = (uploads or [])[:max_files]
            # mantener inmutabilidad del comando para trazabilidad
            cmd = replace(cmd, uploads=uploads)

        # 3) Requeridos (salvo proveedor con JSON válido más abajo)
        if getattr(question, "required", False):
            if not (has_text or has_choice or has_uploads):
                raise ValidationError(message="La pregunta es obligatoria.", field="answer")

        # 4) ¿Es pregunta de actor?
        from app.domain.rules import is_actor_tag
        is_actor_question = is_actor_tag(tag)

        # 5) ¿Es PROVEEDOR con lista JSON?
        rows_from_json: List[Dict[str, Any]] = []
        used_multi = False
        if tag == "proveedor" and has_text:
            s = (answer_text or "").strip()
            if s.startswith("[") and s.endswith("]"):
                rows_from_json = self._parse_proveedor_rows(s)
                used_multi = True

        saved = None
        multi_count = 0

        if used_multi and rows_from_json:
            # --------- Rama proveedor (merge por clave, sin limpiar) ----------
            # Clave de merge por proveedor: (nombre.lower(), orden_compra.lower())
            def key_of(meta_or_row: Dict[str, Any]) -> tuple[str, str]:
                return (
                    str((meta_or_row.get("nombre") or meta_or_row.get("Nombre") or "")).strip().lower(),
                    str((meta_or_row.get("orden_compra") or meta_or_row.get("oc") or "")).strip().lower(),
                )

            # Cargar existentes de esta pregunta en el submission
            existing = [
                a for a in self.answer_repo.list_by_submission(submission.id)
                if str(a.question_id) == str(question.id)
            ]
            existing_by_key: Dict[tuple[str, str], DAnswer] = {}
            for a in existing:
                row_meta = dict(a.meta or {})
                row_meta["nombre"] = a.answer_text or row_meta.get("nombre", "")
                k = key_of(row_meta)
                existing_by_key[k] = a

            # Merge: actualizar si existe, crear si no
            for row in rows_from_json:
                k = key_of(row)
                base_meta = {
                    "estibas": row["estibas"],
                    "orden_compra": row["orden_compra"],
                    "recipientes": row["recipientes"],
                    "unidad": row["unidad"],
                }

                if k in existing_by_key:
                    # inmutabilidad: nueva entidad con meta/texto actualizados
                    prev = existing_by_key[k]
                    entity = prev.with_text(row["nombre"]).with_meta(base_meta)
                    saved = self.answer_repo.save(entity)
                else:
                    entity = DAnswer.create_new(
                        submission_id=submission.id,
                        question_id=question.id,
                        user_id=user_id,            # compat con repos/entidad actuales
                        answer_text=row["nombre"],
                        answer_choice_id=None,
                        answer_file_path=None,
                        ocr_meta=None,
                        meta=base_meta,
                    )
                    saved = self.answer_repo.save(entity)
                multi_count += 1

            # Importante: no truncamos futuras respuestas ni limpiamos la pregunta
            next_qid = None  # se resuelve con la lógica general más abajo

        else:
            # ---------------------- Rama clásica (una respuesta) ----------------
            # 6) Truncar futuras respuestas
            if force_truncate_future:
                self.answer_repo.delete_after_question(
                    submission_id=submission.id, question_id=question.id
                )

            # 7) Limpiar SOLO en preguntas no-proveedor (comportamiento actual)
            if tag != "proveedor":
                self.answer_repo.clear_for_question(
                    submission_id=submission.id,
                    question_id=question.id,
                )

            # 8) Guardar la respuesta única
            saved_path: Optional[str] = None
            if has_uploads:
                uf = uploads[0]
                saved_path = self.storage.save(
                    folder=f"submissions/{submission.id}", file_obj=uf
                )

            entity = DAnswer.create_new(
                submission_id=submission.id,
                question_id=question.id,
                user_id=user_id,  # compat
                answer_text=answer_text,
                answer_choice_id=answer_choice_id,
                answer_file_path=saved_path,
                ocr_meta=None,
                meta=None,
            )
            saved = self.answer_repo.save(entity)
            multi_count = 1

            # 9) Efectos derivados: mapear actor explícito al submission
            if actor_id and is_actor_question:
                field_map = {
                    "proveedor": "proveedor_id",
                    "transportista": "transportista_id",
                    "receptor": "receptor_id",
                }
                target = field_map.get(tag)
                if target:
                    self.submission_repo.save_partial_updates(submission.id, **{target: actor_id})

        # 10) Resolver siguiente pregunta
        next_qid = None
        if choice:
            branch = getattr(choice, "branch_to", None) or getattr(choice, "branch_to_id", None)
            if branch:
                next_qid = branch
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
            derived_updates={"multi_count": multi_count},
            warnings=[],
        )
