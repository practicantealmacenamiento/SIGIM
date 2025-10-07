from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Ajusta a tu app real
from app.infrastructure.models import Questionnaire, Question, Choice


def _map_type(forms_type: str) -> str:
    t = (forms_type or "").lower()
    if t == "question.fileupload":
        return "file"
    if t == "question.choice":
        return "choice"
    if t == "question.textfield":
        return "text"
    if t == "question.datetime":
        return "date"
    return "text"


def _infer_file_mode(_: dict) -> str:
    # Predeterminado seguro para uploads
    return "image_only"


def _infer_semantic_tag(title: str) -> str:
    if not title:
        return "none"
    t = title.lower()
    if "placa" in t:
        return "placa"
    if "precinto" in t:
        return "precinto"
    if "contenedor" in t:
        return "contenedor"
    return "none"


def _parse_question_info(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _choices_from_question_info(qinfo: dict) -> List[dict]:
    out = []
    for c in (qinfo.get("Choices") or []):
        text = (c.get("Description") or c.get("FormsProDisplayRTText") or "").strip()
        bi = c.get("BranchInfo") or {}
        branch = (bi.get("TargetQuestionId") or "") or None
        if text:
            out.append({"text": text, "branch_target_external_id": branch})
    return out


class Command(BaseCommand):
    help = "Importa un cuestionario desde un JSON de Microsoft Forms al modelo del proyecto."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Ruta al archivo JSON exportado (arreglo de preguntas).")
        parser.add_argument("--qid", type=str, default=None, help="UUID de Questionnaire existente a ACTUALIZAR.")
        parser.add_argument("--title", type=str, default=None, help="Título del cuestionario (si se crea).")
        parser.add_argument("--qversion", type=str, default="v1", help="Versión del cuestionario (si se crea).")
        parser.add_argument("--timezone", type=str, default="America/Bogota", help="Time zone (si se crea).")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Si se pasa junto a --qid, borra TODAS las preguntas/opciones actuales y recrea desde el JSON."
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        json_path = Path(opts["json_path"])
        if not json_path.exists():
            raise CommandError(f"No existe el archivo: {json_path}")

        try:
            forms_items = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(forms_items, list):
                raise ValueError("El JSON debe ser un arreglo de preguntas.")
        except Exception as e:
            raise CommandError(f"JSON inválido: {e}")

        qid = opts.get("qid")
        title = opts.get("title")
        qversion = opts.get("qversion")
        timezone = opts.get("timezone")
        replace = bool(opts.get("replace"))

        # 1) Obtener o crear Questionnaire
        if qid:
            try:
                questionnaire = Questionnaire.objects.get(id=uuid.UUID(str(qid)))
            except Questionnaire.DoesNotExist:
                raise CommandError(f"Questionnaire {qid} no existe.")
        else:
            if not title:
                raise CommandError("Debes enviar --title para crear un cuestionario nuevo.")
            questionnaire = Questionnaire.objects.create(
                title=title.strip(),
                version=(qversion or "v1").strip(),
                timezone=(timezone or "America/Bogota").strip(),
            )

        self.stdout.write(self.style.SUCCESS(f"Usando Questionnaire: {questionnaire.id} – {getattr(questionnaire, 'title', '')}"))

        # Normaliza orden
        def _safe_int(x, default=0):
            try:
                return int(x)
            except Exception:
                return default

        forms_items_sorted = sorted(forms_items, key=lambda it: _safe_int(it.get("order"), 0))

        # Si --replace: borramos TODO lo actual (preguntas/opciones). Cascade borra Choice al borrar Question.
        if replace and qid:
            deleted, _ = Question.objects.filter(questionnaire=questionnaire).delete()
            self.stdout.write(self.style.WARNING(f"--replace activo: eliminadas {deleted} filas (preguntas y opciones cascada)."))

        # Mapa: id externo (Forms) -> UUID pregunta creada
        external_to_db_qid: Dict[str, uuid.UUID] = {}

        # 2) Primera pasada: crear/actualizar preguntas + opciones (sin branches)
        for i, item in enumerate(forms_items_sorted):
            ext_id = item.get("id")
            q_text = (item.get("title") or "").strip()
            qtype = _map_type(item.get("type"))
            required = bool(item.get("required"))
            order = _safe_int(item.get("order"), i + 1)
            qinfo = _parse_question_info(item.get("questionInfo"))
            file_mode = _infer_file_mode(qinfo) if qtype == "file" else ""

            if replace:
                # siempre crear desde cero
                qobj = Question.objects.create(
                    questionnaire=questionnaire,
                    text=q_text,
                    type=qtype,
                    required=required,
                    order=order,
                    file_mode=(file_mode or "image_only") if qtype == "file" else "",
                    semantic_tag=_infer_semantic_tag(q_text),
                )
            else:
                # modo sincronización (idempotente por texto)
                qobj = (
                    Question.objects
                    .filter(questionnaire=questionnaire, text=q_text)
                    .order_by("order")
                    .first()
                )
                if qobj:
                    qobj.type = qtype
                    qobj.required = required
                    qobj.order = order
                    qobj.file_mode = (file_mode or "image_only") if qtype == "file" else ""
                    qobj.semantic_tag = _infer_semantic_tag(q_text)
                    qobj.save()
                else:
                    qobj = Question.objects.create(
                        questionnaire=questionnaire,
                        text=q_text,
                        type=qtype,
                        required=required,
                        order=order,
                        file_mode=(file_mode or "image_only") if qtype == "file" else "",
                        semantic_tag=_infer_semantic_tag(q_text),
                    )

            if ext_id:
                external_to_db_qid[ext_id] = qobj.id

            # Opciones (sin branch_to)
            if qtype == "choice":
                forms_choices = _choices_from_question_info(qinfo)
                if replace:
                    # crear directo
                    for c in forms_choices:
                        txt = c["text"].strip()
                        if txt:
                            Choice.objects.create(question=qobj, text=txt, branch_to=None)
                else:
                    # sincronizar
                    existing = {c.text.strip().lower(): c for c in qobj.choices.all()}
                    seen = set()
                    for c in forms_choices:
                        txt = c["text"].strip()
                        if not txt:
                            continue
                        key = txt.lower()
                        if key in existing:
                            ch = existing[key]
                            ch.text = txt
                            ch.branch_to = None
                            ch.save()
                        else:
                            Choice.objects.create(question=qobj, text=txt, branch_to=None)
                        seen.add(key)
                    for k, ch in list(existing.items()):
                        if k not in seen:
                            ch.delete()

        # 3) Segunda pasada: resolver branch_to usando el mapa external_to_db_qid
        for item in forms_items:
            if _map_type(item.get("type")) != "choice":
                continue
            q_text = (item.get("title") or "").strip()
            qinfo = _parse_question_info(item.get("questionInfo"))
            forms_choices = _choices_from_question_info(qinfo)

            qobj = Question.objects.filter(questionnaire=questionnaire, text=q_text).first()
            if not qobj:
                continue

            # índice por texto
            choice_by_text = {c.text.strip().lower(): c for c in qobj.choices.all()}
            for c in forms_choices:
                txt = c["text"].strip().lower()
                branch_ext = c["branch_target_external_id"]
                if not txt or not branch_ext:
                    continue
                branch_db_qid = external_to_db_qid.get(branch_ext)
                ch = choice_by_text.get(txt)
                if ch and branch_db_qid:
                    ch.branch_to = Question.objects.filter(id=branch_db_qid).first()
                    ch.save()

        self.stdout.write(self.style.SUCCESS("Importación completada."))
        self.stdout.write(f"Questionnaire ID: {questionnaire.id}")
