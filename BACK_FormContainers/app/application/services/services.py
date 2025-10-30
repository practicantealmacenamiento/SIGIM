"""
Servicios (casos de uso) de la capa de aplicación.

Reglas:
- Dependen SOLO de puertos del dominio (repos/external ports).
- No conocen ORM ni adaptadores; eso vive en infraestructura.
- Orquestan entidades y reglas de negocio.

Incluye:
- AnswerService
- SubmissionService
- HistoryService
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, date
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from app.domain import rules
from app.domain.entities import Answer
from app.domain.exceptions import EntityNotFoundError, DomainException
from app.domain.ports.external_ports import FileStorage
from app.domain.ports.repositories import (
    AnswerRepository,
    QuestionRepository,
    SubmissionRepository,
    UserPK,
)
from app.application.commands import CreateAnswerCommand, UpdateAnswerCommand, UNSET

__all__ = ["AnswerService", "SubmissionService", "HistoryService"]


# ==============================================================================
#   AnswerService
# ==============================================================================

class AnswerService:
    """CRUD de Answer + manejo de archivo único via FileStorage."""

    def __init__(self, *, repo: AnswerRepository, storage: FileStorage) -> None:
        self.repo = repo
        self.storage = storage

    # ---- Commands ----

    def create_answer(self, cmd: CreateAnswerCommand) -> Answer:
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

        # Archivo (tri-estado)
        if getattr(cmd, "answer_file", UNSET) is not UNSET:
            old_path = entity.answer_file_path
            if cmd.answer_file is None:
                entity.update_file_path(None)
            else:
                new_path = self._store_answer_file(cmd.answer_file)
                entity.update_file_path(new_path)
                if old_path and cmd.delete_old_file_on_replace:
                    self.storage.delete(path=old_path)  # best-effort

        # Metadatos
        if cmd.ocr_meta is not UNSET:
            entity.set_ocr_meta(cmd.ocr_meta or {})
        if cmd.meta is not UNSET:
            entity.set_meta(cmd.meta or {})

        return self.repo.save(entity)

    def delete_answer(self, id: UUID) -> None:
        self.repo.delete(id)

    # ---- Queries ----

    def get_answer(self, id: UUID) -> Optional[Answer]:
        return self.repo.get(id)

    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[Answer]:
        return self.repo.list_by_user(user_id, limit=limit)

    def list_by_submission(self, submission_id: UUID) -> List[Answer]:
        return self.repo.list_by_submission(submission_id)

    def list_by_question(self, question_id: UUID) -> List[Answer]:
        return self.repo.list_by_question(question_id)

    # ---- Internos ----

    def _store_answer_file(self, file_obj) -> str:
        today = datetime.now(timezone.utc)
        folder = os.path.join("uploads", f"{today.year:04d}", f"{today.month:02d}", f"{today.day:02d}")
        return self.storage.save(folder=folder, file_obj=file_obj)


def _norm_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    t = value.strip()
    return t or None


# ==============================================================================
#   SubmissionService
# ==============================================================================

class SubmissionService:
    """
    Casos de uso de Submission.
    Nota: expone métodos pensados para vistas delgadas.
    """

    _FASES_PERMITIDAS = {"entrada", "salida"}

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

    # ---- Commands ----

    def create_submission(
        self,
        *,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID] = None,
        placa_vehiculo: Optional[str] = None,
        created_by: Optional[Any] = None,
    ):
        """
        Crea la submission aplicando validaciones ligeras y normalizaciones.
        Delegamos la persistencia en el repositorio.
        """
        # 1) Validar fase
        t = (tipo_fase or "").strip().lower()
        if t not in self._FASES_PERMITIDAS:
            raise DomainException(message=f"tipo_fase inválido: '{tipo_fase}'", code="invalid_phase")

        # 2) Normalizar placa si viene
        placa_norm: Optional[str] = None
        if placa_vehiculo:
            placa_norm = rules.normalizar_placa(placa_vehiculo or "")
            if not placa_norm or placa_norm == "NO_DETECTADA":
                placa_norm = None

        # 3) (Opcional) Comprobación de existencia de questionnaire
        #    No contamos con QuestionnaireRepository en este servicio; si se añade,
        #    aquí deberíamos verificar su existencia y lanzar EntityNotFoundError.

        return self.submission_repo.create_submission(
            questionnaire_id=questionnaire_id,
            tipo_fase=t,  # usamos la versión normalizada
            regulador_id=regulador_id,
            placa_vehiculo=placa_norm,
            created_by=created_by,
        )

    def finalize_submission(self, submission_id: UUID) -> Dict:
        """
        Marca como finalizada una submission (idempotente) y deriva placa si falta.
        Devuelve solo los campos actualizados (para que la vista responda 200 con el diff).
        """
        sub = self.submission_repo.get(submission_id)
        if not sub:
            raise EntityNotFoundError(
                message="Submission no encontrada.",
                entity_type="Submission",
                entity_id=str(submission_id),
            )

        # Idempotencia: si ya está finalizada, devolvemos el estado actual sin modificar
        if getattr(sub, "finalizado", False):
            return {
                "finalizado": True,
                "fecha_cierre": sub.fecha_cierre,
                "placa_vehiculo": getattr(sub, "placa_vehiculo", None),
            }

        updates = {
            "finalizado": True,
            "fecha_cierre": datetime.now(timezone.utc),
        }

        current_plate = getattr(sub, "placa_vehiculo", None)
        if not current_plate:
            derived = self._derive_plate_from_answers(submission_id)
            if derived:
                updates["placa_vehiculo"] = derived

        self.submission_repo.save_partial_updates(submission_id, **updates)
        return updates

    # ---- Queries pensadas para DRF (pragmáticas) ----

    def list_submissions(self, params, *, user=None, include_all: bool = False):
        """
        Normaliza filtros a un dict simple y delega en el repo.
        La vista puede enviar `request.query_params`; aquí lo transformamos.
        """
        filters = self._parse_filters(params)
        return self.submission_repo.list_for_api(filters, user=user, include_all=include_all)

    def get_submission_for_api(self, id: UUID, *, user=None, include_all: bool = False):
        """
        Devuelve el modelo con relaciones para serializar directamente en DRF.
        (Evita que la vista toque repositorios).
        """
        return self.submission_repo.get_for_api(id, user=user, include_all=include_all)

    def get_submission_enriched(self, id: UUID, *, user=None, include_all: bool = False):
        """
        Devuelve el modelo con respuestas/preguntas prefetch-eadas para detalle enriquecido.
        """
        return (
            self.submission_repo
            .detail_queryset(user=user, include_all=include_all)
            .filter(id=id)
            .first()
        )

    # ---- Query de dominio (opcional) ----

    def get_detail(self, submission_id: UUID) -> Dict:
        """
        Devuelve dict de dominio: submission + answers con `question` rehidratada.
        Útil si prefieres serializar entidades en vez de modelos.
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
        # Se asume un método get(...) estándar en QuestionRepository
        question_map = {q.id: q for q in (self.question_repo.list_by_ids(q_ids) if hasattr(self.question_repo, "list_by_ids") else [self.question_repo.get(qid) for qid in q_ids] if q_ids else []) if q}

        for ans in answers:
            ans.question = question_map.get(ans.question_id)

        return {"submission": submission, "answers": answers}

    # ---- Internos ----

    def _derive_plate_from_answers(self, submission_id: UUID) -> Optional[str]:
        answers = self.answer_repo.list_by_submission(submission_id)
        if not answers:
            return None

        # Prioriza preguntas con semantic_tag == 'placa'
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

    def _parse_filters(self, params: Any) -> Dict[str, Any]:
        """
        Convierte params (QueryDict/dict) a un dict tipado para repo.
        - Booleans seguros
        - UUIDs opcionales
        - Fechas (date) opcionalmente
        - Strings saneados
        """
        def _b(key: str, default: Optional[bool] = None) -> Optional[bool]:
            v = (params.get(key) if hasattr(params, "get") else params.get(key, None))  # soporta QueryDict/dict
            if v is None:
                return default
            s = str(v).strip().lower()
            if s in ("1", "true", "t", "yes", "y"):
                return True
            if s in ("0", "false", "f", "no", "n"):
                return False
            return default

        def _u(key: str) -> Optional[UUID]:
            v = (params.get(key) if hasattr(params, "get") else params.get(key, None))
            if not v:
                return None
            try:
                return UUID(str(v))
            except Exception:
                return None

        def _s(key: str) -> Optional[str]:
            v = (params.get(key) if hasattr(params, "get") else params.get(key, None))
            if v is None:
                return None
            s = str(v).strip()
            return s or None

        def _d(key: str) -> Optional[date]:
            v = _s(key)
            if not v:
                return None
            try:
                # Permitimos YYYY-MM-DD
                y, m, d = v.split("-")
                return date(int(y), int(m), int(d))
            except Exception:
                return None

        filtros: Dict[str, Any] = {}

        incluir_borradores = _b("incluir_borradores", default=False)
        if incluir_borradores is not None:
            filtros["incluir_borradores"] = incluir_borradores

        solo_finalizados = _b("solo_finalizados", default=None)
        if solo_finalizados is not None:
            filtros["solo_finalizados"] = solo_finalizados

        tipo_fase = _s("tipo_fase")
        if tipo_fase:
            tf = tipo_fase.lower()
            if tf in self._FASES_PERMITIDAS:
                filtros["tipo_fase"] = tf

        placa = _s("placa_vehiculo")
        if placa:
            filtros["placa_vehiculo"] = placa

        contenedor = _s("contenedor")
        if contenedor:
            filtros["contenedor"] = contenedor

        for k in ("proveedor_id", "transportista_id", "receptor_id"):
            u = _u(k)
            if u:
                filtros[k] = u

        f_desde = _d("fecha_desde")
        if f_desde:
            filtros["fecha_desde"] = f_desde

        f_hasta = _d("fecha_hasta")
        if f_hasta:
            filtros["fecha_hasta"] = f_hasta

        solo_pend_s2 = _b("solo_pendientes_fase2", default=None)
        if solo_pend_s2 is not None:
            filtros["solo_pendientes_fase2"] = solo_pend_s2

        return filtros


# ==============================================================================
#   HistoryService
# ==============================================================================

class HistoryService:
    """Agregación de historial por regulador y derivaciones auxiliares."""

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

    def list_history(
        self,
        *,
        fecha_desde=None,
        fecha_hasta=None,
        solo_completados: bool = False,
        user=None,
        include_all: bool = False,
    ) -> List[Dict]:
        rows = self.submission_repo.history_aggregate(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            user=user,
            include_all=include_all,
        )
        f1_ids = [row["fase1_id"] for row in rows if row["fase1_id"]]
        f2_ids = [row["fase2_id"] for row in rows if row["fase2_id"]]
        sub_map = self.submission_repo.get_by_ids(
            f1_ids + f2_ids,
            user=user,
            include_all=include_all,
        )

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

            items.append({
                "regulador_id": row["regulador_id"],
                "placa_vehiculo": placa or None,
                "contenedor": (getattr(f2, "contenedor", None) if f2 else None) or (getattr(f1, "contenedor", None) if f1 else None),
                "ultima_fecha_cierre": row["ultima_fecha_cierre"],
                "fase1": f1,
                "fase2": f2,
            })

        return items

    # ---- Internos ----

    def _derive_plate_from_answers(self, submission_id: UUID) -> Optional[str]:
        answers = self.answer_repo.list_by_submission(submission_id)
        if not answers:
            return None

        # 1) Preguntas con tag 'placa'
        for a in reversed(answers):
            if not getattr(a, "answer_text", None):
                continue
            q = self.question_repo.get(a.question_id)
            if q and (getattr(q, "semantic_tag", "") or "").lower() == "placa":
                norm = rules.normalizar_placa(a.answer_text or "")
                if norm and norm != "NO_DETECTADA":
                    return norm

        # 2) Fallback: cualquier texto
        for a in reversed(answers):
            if not getattr(a, "answer_text", None):
                continue
            norm = rules.normalizar_placa(a.answer_text or "")
            if norm and norm != "NO_DETECTADA":
                return norm

        return None
