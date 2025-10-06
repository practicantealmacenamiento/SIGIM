from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Subquery, Q

from app.domain.entities import (
    Answer as DAnswer,
    Submission as DSubmission,
    Questionnaire as DQn,
    Question as DQ,
    Choice as DC,
)
from app.domain.repositories import (
    AnswerRepository,
    SubmissionRepository,
    QuestionRepository,
    ChoiceRepository,
    QuestionnaireRepository,
    UserPK,
    ActorRepository,
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
            # Use explicit mapping function to convert entity to model
            self._update_model_from_entity(am, answer)
            am.save()
        except AnswerModel.DoesNotExist:
            # Use explicit mapping function to create model from entity
            am = self._create_model_from_entity(answer)
        return self._model_to_entity(am)

    def get(self, id: UUID) -> Optional[DAnswer]:
        am = (
            AnswerModel.objects.select_related("submission", "question", "answer_choice", "user")
            .filter(id=id)
            .first()
        )
        return self._model_to_entity(am) if am else None

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
        return [self._model_to_entity(x) for x in qs]

    def list_by_submission(self, submission_id: UUID) -> List[DAnswer]:
        qs = (
            AnswerModel.objects.filter(submission_id=submission_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

    def list_by_question(self, question_id: UUID) -> List[DAnswer]:
        qs = (
            AnswerModel.objects.filter(question_id=question_id)
            .select_related("submission", "question", "answer_choice", "user")
            .order_by("timestamp")
        )
        return [self._model_to_entity(x) for x in qs]

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

    # Explicit bidirectional mapping functions
    def _model_to_entity(self, am: AnswerModel) -> DAnswer:
        """Convert AnswerModel to Answer domain entity."""
        return DAnswer.rehydrate(
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

    def _create_model_from_entity(self, answer: DAnswer) -> AnswerModel:
        """Create a new AnswerModel from Answer domain entity."""
        return AnswerModel.objects.create(
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

    def _update_model_from_entity(self, am: AnswerModel, answer: DAnswer) -> None:
        """Update existing AnswerModel with data from Answer domain entity."""
        am.submission_id = answer.submission_id
        am.question_id = answer.question_id
        am.user_id = answer.user_id
        am.answer_text = answer.answer_text
        am.answer_choice_id = answer.answer_choice_id
        am.answer_file = answer.answer_file_path or None
        am.ocr_meta = answer.ocr_meta or {}
        am.meta = answer.meta or {}
        am.timestamp = answer.timestamp


# --------------------------------
# Submission (implementación Django)
# --------------------------------
class DjangoSubmissionRepository(SubmissionRepository):
    def get(self, id: UUID) -> Optional[DSubmission]:
        model = SubmissionModel.objects.filter(id=id).first()
        return self._model_to_entity(model) if model else None

    def save(self, submission: DSubmission) -> DSubmission:
        """Save a submission entity, creating or updating as needed."""
        try:
            model = SubmissionModel.objects.get(id=submission.id)
            self._update_model_from_entity(model, submission)
            model.save()
        except SubmissionModel.DoesNotExist:
            model_data = self._entity_to_model_data(submission)
            model = SubmissionModel.objects.create(**model_data)
        return self._model_to_entity(model)

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
    ) -> Optional[DSubmission]:
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
        model = qs.order_by("-fecha_creacion").first()
        return self._model_to_entity(model) if model else None

    def create_submission(
        self,
        questionnaire_id: UUID,
        tipo_fase: str,
        regulador_id: Optional[UUID] = None,
        placa_vehiculo: Optional[str] = None,
    ) -> DSubmission:
        obj = SubmissionModel.objects.create(
            questionnaire_id=questionnaire_id,
            tipo_fase=tipo_fase,
            regulador_id=regulador_id,
            placa_vehiculo=placa_vehiculo,
        )
        self.ensure_regulador_on_create(obj)
        return self._model_to_entity(obj)


    def get_fase1_by_regulador(self, regulador_id: UUID) -> Optional[DSubmission]:
        model = (
            SubmissionModel.objects.filter(regulador_id=regulador_id, tipo_fase="entrada")
            .order_by("-fecha_cierre", "-fecha_creacion")
            .first()
        )
        return self._model_to_entity(model) if model else None

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

    def get_detail(self, id: UUID) -> Optional[DSubmission]:
        model = self.detail_queryset().filter(id=id).first()
        return self._model_to_entity(model) if model else None

    def get_for_api(self, id: UUID):
        """
        Devuelve el modelo Django de Submission con relaciones y respuestas
        prefetch-eadas para serialización en la API.
        """
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
            .distinct()  # Evitar duplicados
            .order_by("-ultima_fecha_cierre")
        )

    def get_by_ids(self, ids):
        qs = (
            SubmissionModel.objects.filter(id__in=ids)
            .select_related("questionnaire", "proveedor", "transportista", "receptor")
        )
        return {str(s.id): s for s in qs}

    # Explicit bidirectional mapping functions
    def _model_to_entity(self, model: SubmissionModel) -> DSubmission:
        """Convert SubmissionModel to Submission domain entity."""
        return DSubmission(
            id=model.id,
            questionnaire_id=model.questionnaire_id,
            tipo_fase=model.tipo_fase,
            regulador_id=model.regulador_id,
            placa_vehiculo=model.placa_vehiculo,
            finalizado=model.finalizado,
            fecha_creacion=model.fecha_creacion,
            fecha_cierre=model.fecha_cierre,
        )

    def _entity_to_model_data(self, entity: DSubmission) -> Dict[str, Any]:
        """Convert Submission domain entity to model data dictionary."""
        return {
            'id': entity.id,
            'questionnaire_id': entity.questionnaire_id,
            'tipo_fase': entity.tipo_fase,
            'regulador_id': entity.regulador_id,
            'placa_vehiculo': entity.placa_vehiculo,
            'finalizado': entity.finalizado,
            'fecha_creacion': entity.fecha_creacion,
            'fecha_cierre': entity.fecha_cierre,
        }

    def _update_model_from_entity(self, model: SubmissionModel, entity: DSubmission) -> None:
        """Update existing SubmissionModel with data from Submission domain entity."""
        model.questionnaire_id = entity.questionnaire_id
        model.tipo_fase = entity.tipo_fase
        model.regulador_id = entity.regulador_id
        model.placa_vehiculo = entity.placa_vehiculo
        model.finalizado = entity.finalizado
        model.fecha_creacion = entity.fecha_creacion
        model.fecha_cierre = entity.fecha_cierre


# ------------------------------
# Question (implementación Django)
# ------------------------------
class DjangoQuestionRepository(QuestionRepository):
    def get(self, id: UUID) -> Optional[DQ]:
        model = QuestionModel.objects.filter(id=id).prefetch_related("choices").first()
        return self._model_to_entity(model) if model else None

    def list_by_questionnaire(self, questionnaire_id: UUID) -> List[DQ]:
        models = list(QuestionModel.objects.filter(questionnaire_id=questionnaire_id).order_by("order").prefetch_related("choices"))
        return [self._model_to_entity(model) for model in models]

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

    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[DQ]:
        model = (
            QuestionModel.objects.filter(questionnaire_id=questionnaire_id, order__gt=order)
            .order_by("order")
            .prefetch_related("choices")
            .first()
        )
        return self._model_to_entity(model) if model else None
    
    def get_by_id(self, id: str) -> Optional[QuestionModel]:
        """
        Retorna el modelo Question por id (UUID en str) o None si no existe.
        No lanza excepción hacia la vista.
        """
        try:
            return QuestionModel.objects.get(id=id)
        except QuestionModel.DoesNotExist:
            return None

    # Explicit mapping functions
    def _model_to_entity(self, model: QuestionModel) -> DQ:
        """Convert QuestionModel to Question domain entity."""
        choices = []
        # Solo incluir opciones para preguntas de tipo 'choice'
        if model.type == "choice" and hasattr(model, 'choices'):
            for choice_model in model.choices.all():
                choices.append(DC(
                    id=choice_model.id,
                    text=choice_model.text,
                    branch_to=choice_model.branch_to_id
                ))
        
        return DQ(
            id=model.id,
            text=model.text,
            type=model.type,
            required=model.required,
            order=model.order,
            choices=tuple(choices) if choices else None,
            semantic_tag=model.semantic_tag,
            file_mode=model.file_mode,
        )


# ------------------------------
# Choice (implementación Django)
# ------------------------------
class DjangoChoiceRepository(ChoiceRepository):
    def get(self, id: UUID) -> Optional[DC]:
        model = ChoiceModel.objects.filter(id=id).only("id", "text", "branch_to").first()
        return self._model_to_entity(model) if model else None

    # Explicit mapping functions
    def _model_to_entity(self, model: ChoiceModel) -> DC:
        """Convert ChoiceModel to Choice domain entity."""
        return DC(
            id=model.id,
            text=model.text,
            branch_to=model.branch_to_id
        )


# --------------------------------------------
# Actors (queries públicos/admin para catálogos)
# --------------------------------------------
class DjangoActorRepository(ActorRepository):
    def get(self, id: UUID):
        from app.infrastructure.models import Actor as ActorModel
        try:
            obj = ActorModel.objects.get(id=id, activo=True)
            return obj  # devolvemos el modelo; los serializers manuales ya lo toleran
        except ActorModel.DoesNotExist:
            return None
    
    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50):
        from app.infrastructure.models import Actor as ActorModel
        qs = ActorModel.objects.filter(activo=True, tipo=tipo)
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))
        return list(qs.order_by("nombre")[:limit])
    
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
class DjangoQuestionnaireRepository(QuestionnaireRepository):
    """
    Repositorio de Cuestionarios para admin (dominio) y selector público.

    Provee:
      - list_all() / get_by_id() / save()  -> para AdminQuestionnaireViewSet
      - list_minimal()                      -> para selector público
    """

    # --------- Explicit mapping functions --------- #
    def _model_to_entity(self, qn: QuestionnaireModel) -> DQn:
        questions = []
        for q in qn.questions.all().order_by("order").prefetch_related("choices"):
            # Solo incluir opciones para preguntas de tipo 'choice'
            choices = []
            if q.type == "choice":
                choices = [DC(id=c.id, text=c.text, branch_to=(c.branch_to_id or None)) for c in q.choices.all()]
            
            questions.append(
                DQ(
                    id=q.id,
                    text=q.text,
                    type=q.type,
                    required=q.required,
                    order=q.order,
                    choices=tuple(choices) if choices else None,
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
        return [self._model_to_entity(x) for x in qs]

    def get_by_id(self, id: UUID) -> Optional[DQn]:
        qn = (
            QuestionnaireModel.objects
            .filter(id=id)
            .prefetch_related(Prefetch("questions", queryset=QuestionModel.objects.order_by("order").prefetch_related("choices")))
            .first()
        )
        return self._model_to_entity(qn) if qn else None

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
        return self._model_to_entity(qn)

    # --------- API público (selector) --------- #
    def list_minimal(self):
        return (
            QuestionnaireModel.objects
            .only("id", "title", "version")
            .order_by("title", "version")
        )

    @transaction.atomic
    def delete(self, id: UUID) -> bool:
        """Delete a questionnaire by ID. Returns True if deleted, False if not found."""
        try:
            deleted_count, _ = QuestionnaireModel.objects.filter(id=id).delete()
            return deleted_count > 0
        except Exception:
            return False