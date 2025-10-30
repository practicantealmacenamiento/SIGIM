"""Servicios de aplicaion para el panel de administración con el fin de mantener las vistas de adiminstración limpias 
    y enfocadas en la lógica de flujo HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Count, F, Max, Prefetch, Q

from app.infrastructure.models import Actor, Choice, Question, Questionnaire

UserModel = get_user_model()
ACTOR_TYPES = {code for code, _ in Actor.Tipo.choices}
TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def _clean_str(value: Optional[str]) -> str:
    return (value or "").strip()


def _as_bool(value, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in TRUE_VALUES


def _validate_question_type(t: Optional[str]) -> str:
    allowed = {code for code, _ in Question.TYPE_CHOICES}
    candidate = _clean_str(t) or "text"
    return candidate if candidate in allowed else "text"


def _normalize_semantic(value: Optional[str]) -> str:
    allowed = {code for code, _ in Question.SEMANTIC_CHOICES}
    candidate = _clean_str(value).lower()
    if not candidate or candidate == "none":
        return "none"
    return candidate if candidate in allowed else "none"


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------

class AdminActorService:
    def filtered_queryset(self, *, search: str = "", tipo: str = ""):
        qs = Actor.objects.all()
        search = _clean_str(search)
        tipo = _clean_str(tipo).upper()

        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))
        if tipo and tipo in ACTOR_TYPES:
            qs = qs.filter(tipo=tipo)
        return qs.order_by("nombre")

    def retrieve(self, pk) -> Actor:
        return Actor.objects.get(pk=pk)

    def create(self, data: dict) -> Actor:
        tipo = _clean_str(data.get("tipo")).upper()
        if tipo not in ACTOR_TYPES:
            tipo = Actor.Tipo.RECEPTOR
        return Actor.objects.create(
            nombre=data.get("nombre", ""),
            tipo=tipo,
            documento=data.get("documento") or data.get("nit"),
            activo=_as_bool(data.get("activo"), default=True),
        )

    def update(self, actor: Actor, data: dict) -> Actor:
        if "nombre" in data:
            actor.nombre = data["nombre"]
        if "documento" in data or "nit" in data:
            actor.documento = data.get("documento", data.get("nit"))
        if "tipo" in data:
            candidate = _clean_str(data.get("tipo")).upper()
            if candidate in ACTOR_TYPES:
                actor.tipo = candidate
        if "activo" in data:
            actor.activo = _as_bool(data.get("activo"), default=actor.activo)
        actor.save()
        return actor

    def delete(self, actor: Actor) -> None:
        actor.delete()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class AdminUserService:
    def list_all(self):
        return UserModel.objects.all()

    def retrieve(self, pk):
        return UserModel.objects.get(pk=pk)

    def create(self, data: dict):
        data = data.copy()
        password = data.pop("password", None)
        if password:
            data["password"] = make_password(password)
        return UserModel.objects.create(**data)

    def update(self, instance, data: dict, *, partial: bool = False):
        data = data.copy()
        password = data.pop("password", None)
        for field, value in data.items():
            if partial and value is None:
                continue
            setattr(instance, field, value)
        if password:
            instance.password = make_password(password)
        instance.save()
        return instance

    def delete(self, instance) -> None:
        instance.delete()


# ---------------------------------------------------------------------------
# Questionnaires
# ---------------------------------------------------------------------------

@dataclass
class QuestionnaireBranchLink:
    choice: Choice
    target_id: Optional[str]


class AdminQuestionnaireService:
    BIG_OFFSET = 1_000_000

    # --- Query helpers ----------------------------------------------------
    def list_queryset(self):
        return (
            Questionnaire.objects.annotate(questions_count=Count("questions"))
            .only("id", "title", "version", "timezone")
            .order_by("title")
        )

    def filtered_queryset(self, *, search: str = ""):
        qs = self.list_queryset()
        term = _clean_str(search)
        if term:
            qs = qs.filter(Q(title__icontains=term) | Q(version__icontains=term))
        return qs

    def retrieve(self, pk: str):
        return (
            Questionnaire.objects.filter(pk=pk)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=Question.objects.order_by("order").prefetch_related(
                        Prefetch("choices", queryset=Choice.objects.select_related("branch_to").order_by("text"))
                    ),
                )
            )
            .first()
        )

    # --- Create / Update --------------------------------------------------
    @transaction.atomic
    def create(self, data: dict) -> Questionnaire:
        title = _clean_str(data.get("title"))
        if not title:
            raise ValueError("title_required")

        qn = Questionnaire.objects.create(
            title=title,
            version=_clean_str(data.get("version")) or "v1",
            timezone=_clean_str(data.get("timezone")) or "America/Bogota",
        )

        if isinstance(data.get("questions"), list):
            branch_links: List[QuestionnaireBranchLink] = []
            for idx, qd in enumerate(data["questions"]):
                self._create_or_update_question(
                    questionnaire=qn,
                    payload=qd,
                    is_partial=False,
                    seen_questions=None,
                    branch_links=branch_links,
                    position_hint=idx,
                )
            self._resolve_branch_links(qn, branch_links)

        return self.retrieve(qn.id)

    @transaction.atomic
    def update(self, *, questionnaire_id: str, payload: dict, is_partial: bool) -> Questionnaire:
        qn = (
            Questionnaire.objects.filter(pk=questionnaire_id)
            .prefetch_related(Prefetch("questions", queryset=Question.objects.prefetch_related("choices").order_by("order")))
            .first()
        )
        if not qn:
            raise Questionnaire.DoesNotExist

        if "title" in payload:
            title = _clean_str(payload.get("title"))
            if not title:
                raise ValueError("title_blank")
            qn.title = title
        if "version" in payload:
            version = _clean_str(payload.get("version"))
            if not version:
                raise ValueError("version_blank")
            qn.version = version
        if "timezone" in payload:
            timezone = _clean_str(payload.get("timezone"))
            if not timezone:
                raise ValueError("timezone_blank")
            qn.timezone = timezone
        qn.save()

        if "questions" in payload and isinstance(payload.get("questions"), list):
            existing_qs = {str(q.id): q for q in qn.questions.all()}
            branch_links: List[QuestionnaireBranchLink] = []
            seen_qids: set[str] = set()

            for idx, qd in enumerate(payload["questions"]):
                qid = self._create_or_update_question(
                    questionnaire=qn,
                    payload=qd,
                    is_partial=is_partial,
                    seen_questions=existing_qs,
                    branch_links=branch_links,
                    position_hint=idx,
                )
                if qid:
                    seen_qids.add(qid)

            # Delete removed questions when payload is full replacement
            if not is_partial:
                for qid, question in list(existing_qs.items()):
                    if qid not in seen_qids:
                        question.delete()

            self._resolve_branch_links(qn, branch_links)

        return self.retrieve(qn.id)

    def delete(self, questionnaire: Questionnaire) -> None:
        questionnaire.delete()

    # --- Internal helpers -------------------------------------------------
    def _shift_range(
        self,
        *,
        questionnaire: Questionnaire,
        start: int,
        end: Optional[int],
        direction: str,
        exclude_id: Optional[str] = None,
    ) -> None:
        qs = Question.objects.filter(questionnaire=questionnaire, order__gte=start)
        if end is not None:
            qs = qs.filter(order__lte=end)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        if not qs.exists():
            return

        offset = self.BIG_OFFSET
        qs.update(order=F("order") + offset)

        if direction == "up":
            qs.update(order=F("order") - (offset - 1))
        else:
            qs.update(order=F("order") - (offset + 1))

    def _create_or_update_question(
        self,
        *,
        questionnaire: Questionnaire,
        payload: dict,
        is_partial: bool,
        seen_questions: Optional[dict],
        branch_links: List[QuestionnaireBranchLink],
        position_hint: int,
    ) -> Optional[str]:
        qid = _clean_str(payload.get("id")) or None

        text_present = "text" in payload
        type_present = "type" in payload
        req_present = "required" in payload
        order_present = "order" in payload
        sem_present = "semantic_tag" in payload
        fm_present = "file_mode" in payload

        raw_text = payload.get("text")
        text = _clean_str(raw_text)
        qtype = _validate_question_type(payload.get("type") if type_present else None)
        required = _as_bool(payload.get("required"), default=False) if req_present else None
        semantic_tag = _normalize_semantic(payload.get("semantic_tag") if sem_present else None)
        file_mode = _clean_str(payload.get("file_mode")) if fm_present else None

        new_order: Optional[int] = None
        if order_present:
            try:
                new_order = int(payload.get("order"))
            except Exception:
                new_order = None

        existing_qs = seen_questions or {}

        if qid and qid in existing_qs:
            qobj = existing_qs[qid]
            old_order = qobj.order

            if text_present and raw_text is not None and not (is_partial and text == ""):
                if not text:
                    raise ValueError("question_text_blank")
                qobj.text = text
            if type_present:
                qobj.type = qtype
            if req_present:
                qobj.required = bool(required)
            if sem_present:
                qobj.semantic_tag = semantic_tag
            if fm_present:
                qobj.file_mode = file_mode or "image_only"

            if new_order is not None and new_order != old_order:
                if new_order < old_order:
                    self._shift_range(
                        questionnaire=questionnaire,
                        start=new_order,
                        end=old_order - 1,
                        direction="up",
                        exclude_id=qobj.id,
                    )
                else:
                    self._shift_range(
                        questionnaire=questionnaire,
                        start=old_order + 1,
                        end=new_order,
                        direction="down",
                        exclude_id=qobj.id,
                    )
                qobj.order = new_order

            qobj.save()
        else:
            if not text:
                raise ValueError("question_text_blank")

            if new_order is None:
                max_order = questionnaire.questions.aggregate(m=Max("order"))["m"]
                safe_order = (max_order if max_order is not None else -1) + 1
            else:
                self._shift_range(questionnaire=questionnaire, start=new_order, end=None, direction="up")
                safe_order = new_order

            qobj = Question.objects.create(
                questionnaire=questionnaire,
                text=text,
                type=qtype,
                required=required if req_present else False,
                order=safe_order,
                file_mode=file_mode or "image_only",
                semantic_tag=semantic_tag or "none",
            )
            qid = str(qobj.id)
            if seen_questions is not None:
                seen_questions[qid] = qobj

        if "choices" in payload and isinstance(payload.get("choices"), list):
            existing_cs = {str(c.id): c for c in qobj.choices.all()}
            seen_cids: set[str] = set()

            for choice_payload in payload["choices"]:
                cid = _clean_str(choice_payload.get("id")) or None
                ctext_present = "text" in choice_payload
                raw_ctext = choice_payload.get("text")
                ctext = _clean_str(raw_ctext)
                branch_to = _clean_str(choice_payload.get("branch_to")) or None

                if cid and cid in existing_cs:
                    cobj = existing_cs[cid]
                    if ctext_present and raw_ctext is not None and not (is_partial and ctext == ""):
                        if not ctext:
                            raise ValueError("choice_text_blank")
                        cobj.text = ctext
                    cobj.branch_to = None
                    cobj.save()
                else:
                    if not ctext:
                        raise ValueError("choice_text_blank")
                    cobj = Choice.objects.create(question=qobj, text=ctext, branch_to=None)
                    cid = str(cobj.id)
                    if seen_questions is not None:
                        existing_cs[cid] = cobj

                seen_cids.add(cid)
                branch_links.append(QuestionnaireBranchLink(choice=cobj, target_id=branch_to))

            if not is_partial:
                for cid, cobj in list(existing_cs.items()):
                    if cid not in seen_cids:
                        cobj.delete()

        return qid

    def _resolve_branch_links(self, questionnaire: Questionnaire, links: Iterable[QuestionnaireBranchLink]) -> None:
        if not links:
            return
        questions_index = {
            str(q.id): q
            for q in Questionnaire.objects.filter(pk=questionnaire.id)
            .prefetch_related("questions")
            .first()
            .questions.all()
        }
        for link in links:
            if link.target_id and link.target_id in questions_index:
                link.choice.branch_to = questions_index[link.target_id]
                link.choice.save()
