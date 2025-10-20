# -*- coding: utf-8 -*-
"""
Casos de uso de la capa de aplicación (servicios orquestadores).

Incluye:
- AnswerService: CRUD y manejo de archivo único asociado a una Answer.
- SubmissionService: finalización de submissions y derivación de placa.
- HistoryService: agregación de historial por regulador y derivación auxiliar.

Notas:
- Los servicios coordinan repositorios (persistencia) y puertos (FileStorage).
- Las invariantes principales viven en las entidades de dominio.
- Este módulo no depende de detalles del ORM ni de frameworks.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

# ── Dominio / Aplicación ──────────────────────────────────────────────────────
from app.domain import rules
from app.domain.entities import Answer
from app.domain.exceptions import DomainException, EntityNotFoundError, ValidationError
from app.domain.ports import FileStorage
from app.domain.repositories import AnswerRepository, QuestionRepository, SubmissionRepository, UserPK
from app.application.commands import CreateAnswerCommand, UpdateAnswerCommand, UNSET

__all__ = ["AnswerService", "SubmissionService", "HistoryService"]


# ==============================================================================
#   AnswerService
# ==============================================================================

class AnswerService:
    """
    Casos de uso de Answer (CRUD y orquestación de archivo único).

    Características:
      - Desacoplado del ORM (usa repositorio).
      - La validación de invariantes principales vive en la entidad `Answer`.
      - El almacenamiento de archivos se realiza mediante el puerto `FileStorage`.
    """

    def __init__(self, *, repo: AnswerRepository, storage: FileStorage) -> None:
        self.repo = repo
        self.storage = storage

    # -------------------- Commands -------------------- #

    def create_answer(self, cmd: CreateAnswerCommand) -> Answer:
        """
        Crea una respuesta básica. Si `answer_file` viene definido:
          - Se persiste el archivo con `FileStorage`.
          - Se guarda la ruta lógica en `answer_file_path`.
        """
        file_path = None
        if getattr(cmd, "answer_file", None):
            file_path = self._store_answer_file(cmd.answer_file)

        entity = Answer.create_new(
            submission_id=cmd.submission_id,
            question_id=cmd.question_id,
            user_id=cmd.user_id,
            answer_text=_norm_text(cmd.answer_text),
            answer_choice_id=cmd.answer_choice_id,
            answer_file_path=file_path,
            ocr_meta=cmd.ocr_meta or {},
            meta=cmd.meta or {},
        )
        return self.repo.save(entity)

    def update_answer(self, cmd: UpdateAnswerCommand) -> Answer:
        """
        Actualiza parcialmente una respuesta (semántica tri-estado):
          - UNSET → no tocar.
          - None  → limpiar el valor.
          - valor → asignar el valor.

        Si reemplaza archivo y `delete_old_file_on_replace` es True, intenta
        borrar el archivo anterior mediante `FileStorage` (best-effort).
        """
        entity = self.repo.get(cmd.id)
        if not entity:
            raise EntityNotFoundError(
                message=f"Answer {cmd.id} no encontrada.",
                entity_type="Answer",
                entity_id=str(cmd.id),
            )

        # Texto
        if cmd.answer_text is not UNSET:
            entity.update_text(_norm_text(cmd.answer_text))

        # Choice
        if cmd.answer_choice_id is not UNSET:
            entity.update_choice(cmd.answer_choice_id)

        # Archivo
        if getattr(cmd, "answer_file", UNSET) is not UNSET:
            old_path = entity.answer_file_path
            if cmd.answer_file is None:
                # Limpieza explícita
                entity.update_file_path(None)
            else:
                new_path = self._store_answer_file(cmd.answer_file)
                entity.update_file_path(new_path)
                if old_path and cmd.delete_old_file_on_replace:
                    # Best-effort: si falla, no interrumpimos el flujo
                    self.storage.delete(path=old_path)

        # Metadatos
        if cmd.ocr_meta is not UNSET:
            entity.set_ocr_meta(cmd.ocr_meta or {})
        if cmd.meta is not UNSET:
            entity.set_meta(cmd.meta or {})

        return self.repo.save(entity)

    def delete_answer(self, id: UUID) -> None:
        """
        Elimina la respuesta. La implementación del repositorio/modelo
        se encarga de borrar el archivo físico si existe.
        """
        self.repo.delete(id)

    # -------------------- Queries -------------------- #

    def get_answer(self, id: UUID) -> Optional[Answer]:
        """Obtiene una Answer por id (o None si no existe)."""
        return self.repo.get(id)

    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[Answer]:
        """Lista respuestas de un usuario (con límite opcional)."""
        return self.repo.list_by_user(user_id, limit=limit)

    def list_by_submission(self, submission_id: UUID) -> List[Answer]:
        """Lista respuestas de una submission."""
        return self.repo.list_by_submission(submission_id)

    def list_by_question(self, question_id: UUID) -> List[Answer]:
        """Lista respuestas asociadas a una pregunta (en cualquier submission)."""
        return self.repo.list_by_question(question_id)

    # -------------------- Helpers -------------------- #

    def _store_answer_file(self, file_obj) -> str:
        """
        Persiste el archivo mediante el puerto de storage y devuelve el path relativo.

        Estructura de carpetas:
            uploads/YYYY/MM/DD/
        """
        today = datetime.now(timezone.utc)
        folder = os.path.join("uploads", f"{today.year:04d}", f"{today.month:02d}", f"{today.day:02d}")
        return self.storage.save(folder=folder, file_obj=file_obj)


def _norm_text(value: Optional[str]) -> Optional[str]:
    """
    Normaliza un texto:
      - None → None
      - str → strip() y None si queda vacío
    """
    if value is None:
        return None
    t = value.strip()
    return t if t else None


# ==============================================================================
#   SubmissionService
# ==============================================================================

class SubmissionService:
    """
    Casos de uso de Submission.
      - Finalizar una submission (marca finalizado/fecha_cierre).
      - Derivar placa desde respuestas si no está seteada.
      - Obtener detalle de submission con sus respuestas rehidratadas.
    """

    def __init__(
        self,
        *,
        submission_repo: SubmissionRepository,
        answer_repo: AnswerRepository,
        question_repo: QuestionRepository,
    ) -> None:
        self.submission_repo = submission_repo
        self.answer_repo = answer_repo
        self.question_repo = question_repo

    def finalize_submission(self, submission_id: UUID) -> Dict:
        """
        Marca la submission como finalizada. Si no hay placa en la submission,
        intenta derivarla a partir de respuestas (prioriza preguntas con tag 'placa').

        Retorna:
            dict con los campos actualizados (incluye `finalizado`, `fecha_cierre`
            y `placa_vehiculo` si fue derivada).
        """
        sub = self.submission_repo.get(submission_id)
        if not sub:
            raise EntityNotFoundError(
                message="Submission no encontrada.",
                entity_type="Submission",
                entity_id=str(submission_id),
            )

        updates = {
            "finalizado": True,
            "fecha_cierre": datetime.now(timezone.utc),
        }

        # Solo derivar placa si está vacía en la submission
        current_plate = getattr(sub, "placa_vehiculo", None)
        if not current_plate:
            derived = self._derive_plate_from_answers(submission_id)
            if derived:
                updates["placa_vehiculo"] = derived

        self.submission_repo.save_partial_updates(submission_id, **updates)
        return updates

    # -------------------- Internos -------------------- #

    def _derive_plate_from_answers(self, submission_id: UUID) -> Optional[str]:
        """
        Busca en respuestas de texto de la submission, priorizando aquellas
        cuya pregunta tiene semantic_tag == 'placa'. Si no encuentra, intenta
        con cualquier texto. Usa `rules.normalizar_placa`.
        """
        answers = self.answer_repo.list_by_submission(submission_id)  # ordenadas por timestamp (infra)
        if not answers:
            return None

        # Recorremos de más reciente a más antigua
        def _iter_latest_first(items: List) -> List:
            return list(reversed(items))

        # 1) Respuestas de preguntas con tag 'placa'
        for a in _iter_latest_first(answers):
            if not getattr(a, "answer_text", None):
                continue
            q = self.question_repo.get(a.question_id)
            if not q:
                continue
            if (getattr(q, "semantic_tag", "") or "").lower() != "placa":
                continue
            norm = rules.normalizar_placa(a.answer_text or "")
            if norm and norm != "NO_DETECTADA":
                return norm

        # 2) Fallback: cualquier respuesta de texto
        for a in _iter_latest_first(answers):
            if not getattr(a, "answer_text", None):
                continue
            norm = rules.normalizar_placa(a.answer_text or "")
            if norm and norm != "NO_DETECTADA":
                return norm

        return None

    def get_detail(self, submission_id: UUID) -> Dict:
        """
        Devuelve los detalles de una submission con todas sus respuestas,
        incluyendo las preguntas rehidratadas correctamente.

        Estructura:
            {
              "submission": <objeto submission>,
              "answers": [Answer con atributo `question` poblado]
            }
        """
        submission = self.submission_repo.get(submission_id)
        if not submission:
            raise EntityNotFoundError(
                message="Submission no encontrada.",
                entity_type="Submission",
                entity_id=str(submission_id),
            )

        answers = self.answer_repo.list_by_submission(submission_id)
        q_ids = list({a.question_id for a in answers})
        # Nota: `get_by_ids` se asume disponible en la implementación concreta del repositorio
        question_map = {q.id: q for q in self.question_repo.get_by_ids(q_ids)}

        # Rehidratar referencia a pregunta en cada respuesta (campo auxiliar para vistas)
        for ans in answers:
            ans.question = question_map.get(ans.question_id)

        return {
            "submission": submission,
            "answers": answers,
        }


# ==============================================================================
#   HistoryService
# ==============================================================================

class HistoryService:
    """
    Orquesta el historial por `regulador_id`:
      - Obtiene últimas Fase1/Fase2 (aggregate del repositorio).
      - Deriva placa si no está en la submission (prioriza F2 → F1 → respuestas).
      - Devuelve items listos para serializar.
    """

    def __init__(
        self,
        *,
        submission_repo: SubmissionRepository,
        answer_repo: AnswerRepository,
        question_repo: QuestionRepository,
    ):
        self.submission_repo = submission_repo
        self.answer_repo = answer_repo
        self.question_repo = question_repo

    def list_history(self, *, fecha_desde=None, fecha_hasta=None, solo_completados: bool = False) -> List[Dict]:
        """
        Retorna una lista de ítems de historial. Cada ítem contiene:
          - regulador_id
          - placa_vehiculo (derivada si es posible)
          - contenedor (F2 → F1)
          - ultima_fecha_cierre
          - fase1 / fase2 (objetos submission)
        """
        rows = self.submission_repo.history_aggregate(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
        f1_ids = [row["fase1_id"] for row in rows if row["fase1_id"]]
        f2_ids = [row["fase2_id"] for row in rows if row["fase2_id"]]
        sub_map = self.submission_repo.get_by_ids(f1_ids + f2_ids)

        items: List[Dict] = []
        for row in rows:
            f1 = sub_map.get(str(row["fase1_id"]))
            f2 = sub_map.get(str(row["fase2_id"]))
            if solo_completados and (not f1 or not f2):
                continue

            # Placa: F2 → F1 → derivar de respuestas
            placa = (getattr(f2, "placa_vehiculo", None) if f2 else None) or (getattr(f1, "placa_vehiculo", None) if f1 else None)
            if not placa:
                source = f2 or f1
                if source:
                    placa = self._derive_plate_from_answers(source.id)

            item = {
                "regulador_id": row["regulador_id"],
                "placa_vehiculo": placa or None,
                "contenedor": (getattr(f2, "contenedor", None) if f2 else None) or (getattr(f1, "contenedor", None) if f1 else None),
                "ultima_fecha_cierre": row["ultima_fecha_cierre"],
                "fase1": f1,
                "fase2": f2,
            }
            items.append(item)

        return items

    # ---- Internos ----

    def _derive_plate_from_answers(self, submission_id) -> Optional[str]:
        """
        Recorre respuestas de la submission de más reciente a más antigua:
          - Primero aquellas cuya pregunta tiene semantic_tag == 'placa'.
          - Luego cualquier respuesta de texto.
        Usa `rules.normalizar_placa` para validar el formato.
        """
        answers = self.answer_repo.list_by_submission(submission_id)
        if not answers:
            return None

        # Recorremos de más reciente a más antigua
        for a in reversed(answers):
            if not getattr(a, "answer_text", None):
                continue
            q = self.question_repo.get(a.question_id)
            if q and (getattr(q, "semantic_tag", "") or "").lower() == "placa":
                norm = rules.normalizar_placa(a.answer_text or "")
                if norm and norm != "NO_DETECTADA":
                    return norm

        # Fallback: cualquier texto
        for a in reversed(answers):
            if not getattr(a, "answer_text", None):
                continue
            norm = rules.normalizar_placa(a.answer_text or "")
            if norm and norm != "NO_DETECTADA":
                return norm

        return None
