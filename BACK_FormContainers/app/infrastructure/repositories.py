from __future__ import annotations

from typing import List, Optional, Dict
from uuid import UUID
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Subquery, Q

from app.domain.entities import (
    Answer as DAnswer,
    Questionnaire as DQn,
    Question as DQ,
    Choice as DC,
)
from app.domain.repositories import (
    AnswerRepository,
    SubmissionRepository,
    QuestionRepository,
    ChoiceRepository,
    UserPK,
)
from app.infrastructure.models import (
    Answer as AnswerModel,
    Submission as SubmissionModel,
    Question as QuestionModel,
    Choice as ChoiceModel,
    Actor as ActorModel,
    Questionnaire as QuestionnaireModel
)

# ------------------------------
# Answer (implementación Django)
# ------------------------------
class DjangoAnswerRepository(AnswerRepository):
    @transaction.atomic
    def save(self, answer: DAnswer) -> DAnswer:
        try:
            am = AnswerModel.objects.select_for_update().get(id=answer.id)
            am.submission_id = answer.submission_id
            am.question_id = answer.question_id
            am.user_id = answer.user_id
            am.answer_text = answer.answer_text
            am.answer_choice_id = answer.answer_choice_id
            am.answer_file = answer.answer_file_path or None
            am.ocr_meta = answer.ocr_meta or {}
            am.meta = answer.meta or {}
            am.timestamp = answer.timestamp
            am.save()
        except AnswerModel.DoesNotExist:
            am = AnswerModel.objects.create(
                id=answer.id,
                submission_id=answer.submission_id,
                question_id=answer.question_id,
                user_id=answer.user_id,
                answer_text=answer.answer_text,
                answer_choice_id=answer.answer_choice_id,
                answer_file=answer.answer_file_path or None,
                ocr_meta=answer.ocr_meta or {},
                meta=answer.meta or {},
                timestamp=answer.timestamp,
            )
        return self._rehydrate(am)

    def get(self, id: UUID) -> Optional[DAnswer]:
        am = (
            AnswerModel.objects.select_related("submission", "question", "answer_choice", "user")
            .filter(id=id)
            .first()
        )
        return self._rehydrate(am) if am else None

    @transaction.atomic
    def delete(self, id: UUID) -> None:
        am = AnswerModel.objects.filter(id=id).first()
        if not am:
            return
        if getattr(am, "answer_file", None):
            am.answer_file.delete(save=False)
        am.delete()

    def list_by_user(self, user_id: UserPK, *, limit: Optional[int] = None) -> List[DAnswer]:
        qs = (
            AnswerModel.objects.filter(user_id=user_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("-timestamp")
        )
        if limit:
            qs = qs[:limit]
        return [self._rehydrate(x) for x in qs]

    def list_by_submission(self, submission_id: UUID) -> List[DAnswer]:
        qs = (
            AnswerModel.objects.filter(submission_id=submission_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._rehydrate(x) for x in qs]

    def list_by_question(self, question_id: UUID) -> List[DAnswer]:
        qs = (
            AnswerModel.objects.filter(question_id=question_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._rehydrate(x) for x in qs]

    # helpers
    def _delete_queryset(self, qs) -> int:
        count = 0
        for am in qs:
            if getattr(am, "answer_file", None):
                am.answer_file.delete(save=False)
            am.delete()
            count += 1
        return count

    # operaciones flujo Guardar&Avanzar
    @transaction.atomic
    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        qs = list(
            AnswerModel.objects.filter(
                submission_id=submission_id,
                question_id=question_id,
            )
        )
        return self._delete_queryset(qs)

    @transaction.atomic
    def delete_after_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        q = QuestionModel.objects.filter(id=question_id).only("questionnaire_id", "order").first()
        if not q:
            return 0
        qs = list(
            AnswerModel.objects.filter(
                submission_id=submission_id,
                question__questionnaire_id=q.questionnaire_id,
                question__order__gt=q.order,
            ).select_related("question")
        )
        return self._delete_queryset(qs)

    # mapping ORM -> Dominio
    def _rehydrate(self, am: AnswerModel) -> DAnswer:
        return DAnswer(
            id=am.id,
            submission_id=am.submission_id,
            question_id=am.question_id,
            user_id=am.user_id,
            answer_text=am.answer_text,
            answer_choice_id=am.answer_choice_id,
            answer_file_path=(am.answer_file.name if getattr(am, "answer_file", None) else None),
            ocr_meta=am.ocr_meta or {},
            meta=am.meta or {},
            timestamp=am.timestamp,
        )


# --------------------------------
# Submission (implementación Django)
# --------------------------------
class DjangoSubmissionRepository(SubmissionRepository):
    def get(self, id: UUID):
        return SubmissionModel.objects.filter(id=id).first()

    def save_partial_updates(self, id: UUID, **fields) -> None:
        if not fields:
            return
        sub = SubmissionModel.objects.filter(id=id).first()
        if not sub:
            return
        for k, v in fields.items():
            setattr(sub, k, v)
        sub.save(update_fields=list(fields.keys()))

    # métodos adicionales útiles para interfaces/casos de uso
    def find_recent_draft_without_answers(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID],
        minutes: int = 10,
    ):
        since = timezone.now() - timedelta(minutes=minutes)
        qs = SubmissionModel.objects.filter(
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            finalizado=False,
            fecha_creacion__gte=since,
        )
        if regulador_id is not None:
            qs = qs.filter(regulador_id=regulador_id)
        answers_exists = AnswerModel.objects.filter(submission_id=OuterRef("pk"))
        qs = qs.annotate(has_answers=Exists(answers_exists)).filter(has_answers=False)
        return qs.order_by("-fecha_creacion").first()

    def create_submission(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID] = None,
        placa_vehiculo: Optional[str] = None,
    ):
        obj = SubmissionModel.objects.create(
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
        )
        self.ensure_regulador_on_create(obj)
        return obj


    def get_fase1_by_regulador(self, regulador_id: UUID):
        return (
            SubmissionModel.objects.filter(regulador_id=regulador_id, tipo_fase="entrada")
            .order_by("-fecha_cierre", "-fecha_creacion")
            .first()
        )

    def set_regulador(self, submission_id: UUID, regulador_id: UUID) -> None:
        SubmissionModel.objects.filter(id=submission_id).update(regulador_id=regulador_id)

    # utilidades expuestas en la interfaz
    def list_for_api(self, params):
        qs = (
            SubmissionModel.objects.all()
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
            .order_by("-fecha_creacion")
            .prefetch_related("answers")
        )
        p = params

        if not p.get("incluir_borradores"):
            qs = qs.filter(finalizado=True)
        if p.get("solo_finalizados") in ("1", "true", "True"):
            qs = qs.filter(finalizado=True)

        if p.get("tipo_fase"):
            qs = qs.filter(tipo_fase=p["tipo_fase"])
        if p.get("placa_vehiculo"):
            qs = qs.filter(placa_vehiculo__icontains=p["placa_vehiculo"])
        if p.get("contenedor"):
            qs = qs.filter(contenedor__icontains=p["contenedor"])
        if p.get("proveedor_id"):
            qs = qs.filter(proveedor_id=p["proveedor_id"])
        if p.get("transportista_id"):
            qs = qs.filter(transportista_id=p["transportista_id"])
        if p.get("receptor_id"):
            qs = qs.filter(receptor_id=p["receptor_id"])

        if p.get("fecha_desde"):
            qs = qs.filter(fecha_cierre__date__gte=p["fecha_desde"])
        if p.get("fecha_hasta"):
            qs = qs.filter(fecha_cierre__date__lte=p["fecha_hasta"])

        if p.get("solo_pendientes_fase2") in ("1", "true", "True") and p.get("tipo_fase") == "entrada":
            fase2 = SubmissionModel.objects.filter(
                tipo_fase="salida",
                finalizado=True,
                regulador_id__isnull=False,
                regulador_id=OuterRef("regulador_id"),
            )
            qs = qs.annotate(has_salida_final=Exists(fase2)).filter(has_salida_final=False)
            qs = qs.prefetch_related("answers__question", "answers__answer_choice")

        return qs

    def ensure_regulador_on_create(self, obj: SubmissionModel) -> None:
        if obj.tipo_fase == "entrada" and not obj.regulador_id:
            obj.regulador_id = obj.id
            obj.save(update_fields=["regulador_id"])
            return

        if obj.tipo_fase == "salida" and obj.regulador_id:
            entrada = SubmissionModel.objects.filter(id=obj.regulador_id, tipo_fase="entrada").first()
            if entrada and entrada.regulador_id != obj.regulador_id:
                entrada.regulador_id = obj.regulador_id
                entrada.save(update_fields=["regulador_id"])

    def detail_queryset(self):
        answers_qs = (
            AnswerModel.objects
            .select_related("question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return (
            SubmissionModel.objects
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
            .prefetch_related(Prefetch("answers", queryset=answers_qs))
        )

    def get_detail(self, id: UUID) -> Optional[SubmissionModel]:
        return self.detail_queryset().filter(id=id).first()

    def history_aggregate(self, *, fecha_desde=None, fecha_hasta=None):
        base = SubmissionModel.objects.filter(regulador_id__isnull=False, finalizado=True)

        if fecha_desde:
            base = base.filter(fecha_cierre__date__gte=fecha_desde)
        if fecha_hasta:
            base = base.filter(fecha_cierre__date__lte=fecha_hasta)

        last_f1 = (
            SubmissionModel.objects.filter(
                regulador_id=OuterRef("regulador_id"),
                finalizado=True,
                tipo_fase="entrada",
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("id")[:1]
        )
        last_f2 = (
            SubmissionModel.objects.filter(
                regulador_id=OuterRef("regulador_id"),
                finalizado=True,
                tipo_fase="salida",
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("id")[:1]
        )
        last_date = (
            SubmissionModel.objects.filter(
                regulador_id=OuterRef("regulador_id"),
                finalizado=True,
            )
            .order_by("-fecha_cierre", "-fecha_creacion")
            .values("fecha_cierre")[:1]
        )

        return (
            base.values("regulador_id")
            .annotate(
                fase1_id=Subquery(last_f1),
                fase2_id=Subquery(last_f2),
                ultima_fecha_cierre=Subquery(last_date),
            )
            .order_by("-ultima_fecha_cierre")
        )

    def get_by_ids(self, ids):
        qs = (
            SubmissionModel.objects.filter(id__in=ids)
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
        )
        return {str(s.id): s for s in qs}


# ------------------------------
# Question (implementación Django)
# ------------------------------
class DjangoQuestionRepository(QuestionRepository):
    def get(self, id: UUID) -> Optional[QuestionModel]:
        return QuestionModel.objects.filter(id=id).first()

    def list_by_questionnaire(self, questionnaire_id: UUID):
        return list(QuestionModel.objects.filter(questionnaire_id=questionnaire_id).order_by("order"))

    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]:
        q = QuestionModel.objects.filter(id=current_question_id).only("questionnaire_id", "order").first()
        if not q:
            return None
        next_q = (
            QuestionModel.objects.filter(
                questionnaire_id=q.questionnaire_id,
                order__gt=q.order,
            )
            .order_by("order")
            .only("id")
            .first()
        )
        return next_q.id if next_q else None

    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[QuestionModel]:
        return (
            QuestionModel.objects.filter(questionnaire_id=questionnaire_id, order__gt=order)
            .order_by("order")
            .first()
        )


# ------------------------------
# Choice (implementación Django)
# ------------------------------
class DjangoChoiceRepository(ChoiceRepository):
    def get(self, id: UUID) -> Optional[ChoiceModel]:
        return ChoiceModel.objects.filter(id=id).only("id", "question_id", "branch_to").first()


# --------------------------------------------
# Actors (queries públicos/admin para catálogos)
# --------------------------------------------
class DjangoActorRepository:
    def public_list(self, params):
        qs = ActorModel.objects.filter(activo=True)
        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        search = params.get("search")
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))

        return qs.order_by("nombre")[:50]

    def admin_queryset(self, params):
        qs = ActorModel.objects.all().order_by("nombre")
        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        activo = params.get("activo")
        if activo in ("1", "true", "True"):
            qs = qs.filter(activo=True)
        search = params.get("search")
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))
        return qs


# ---------------------------------------------------------
# Questionnaire (implementación completa para uso en admin)
# ---------------------------------------------------------
class DjangoQuestionnaireRepository:
    """
    Repositorio de Cuestionarios para admin (dominio) y selector público.

    Provee:
      - list_all() / get_by_id() / save()  -> para AdminQuestionnaireViewSet
      - list_minimal()                      -> para selector público
    """

    # --------- Mapping ORM -> Dominio --------- #
    def _to_domain(self, qn: QuestionnaireModel) -> DQn:
        questions = []
        for q in qn.questions.all().order_by("order").prefetch_related("choices"):
            choices = [DC(id=c.id, text=c.text, branch_to=(c.branch_to_id or None)) for c in q.choices.all()]
            questions.append(
                DQ(
                    id=q.id,
                    text=q.text,
                    type=q.type,
                    required=q.required,
                    order=q.order,
                    choices=tuple(choices),
                    semantic_tag=q.semantic_tag,
                    file_mode=q.file_mode,
                )
            )
        return DQn(
            id=qn.id,
            title=qn.title,
            version=qn.version,
            timezone=qn.timezone,
            questions=tuple(questions),
        )

    # --------- API Admin (dominio) --------- #
    def list_all(self) -> List[DQn]:
        qs = (
            QuestionnaireModel.objects
            .prefetch_related(Prefetch("questions", queryset=QuestionModel.objects.order_by("order").prefetch_related("choices")))
            .order_by("title", "version")
        )
        return [self._to_domain(x) for x in qs]

    def get_by_id(self, id: UUID) -> Optional[DQn]:
        qn = (
            QuestionnaireModel.objects
            .filter(id=id)
            .prefetch_related(Prefetch("questions", queryset=QuestionModel.objects.order_by("order").prefetch_related("choices")))
            .first()
        )
        return self._to_domain(qn) if qn else None

    @transaction.atomic
    def save(self, dq: DQn) -> DQn:
        # Upsert del cuestionario
        qn, _created = QuestionnaireModel.objects.update_or_create(
            id=dq.id,
            defaults={
                "title": dq.title,
                "version": dq.version,
                "timezone": dq.timezone,
            },
        )

        # Sincronizar preguntas (upsert + delete faltantes)
        incoming_q_ids = {q.id for q in dq.questions}
        for orm_q in QuestionModel.objects.filter(questionnaire=qn):
            if orm_q.id not in incoming_q_ids:
                orm_q.delete()

        # Upsert preguntas base
        for q in dq.questions:
            orm_q, _ = QuestionModel.objects.update_or_create(
                id=q.id,
                defaults={
                    "questionnaire": qn,
                    "text": q.text,
                    "type": q.type,
                    "required": q.required,
                    "order": q.order,
                    "semantic_tag": q.semantic_tag or "none",
                    "file_mode": q.file_mode or "image_only",
                },
            )

            # Sincronizar choices de la pregunta
            incoming_c_ids = {c.id for c in (q.choices or [])}
            for orm_c in ChoiceModel.objects.filter(question=orm_q):
                if orm_c.id not in incoming_c_ids:
                    orm_c.delete()

            # Upsert choices
            for c in (q.choices or []):
                branch_target = None
                if c.branch_to:
                    # Permite branch a cualquier pregunta existente (se asume misma encuesta)
                    branch_target = QuestionModel.objects.filter(id=c.branch_to).first()
                ChoiceModel.objects.update_or_create(
                    id=c.id,
                    defaults={
                        "question": orm_q,
                        "text": c.text,
                        "branch_to": branch_target,
                    },
                )

        # Recargar con relaciones y devolver en dominio
        qn = (
            QuestionnaireModel.objects
            .filter(id=qn.id)
            .prefetch_related(Prefetch("questions", queryset=QuestionModel.objects.order_by("order").prefetch_related("choices")))
            .first()
        )
        return self._to_domain(qn)

    # --------- API público (selector) --------- #
    def list_minimal(self):
        return (
            QuestionnaireModel.objects
            .only("id", "title", "version")
            .order_by("title", "version")
        )
