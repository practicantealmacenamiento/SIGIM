# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, json, zipfile, xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from app.infrastructure.models import Questionnaire, Question

_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG  = "http://schemas.openxmlformats.org/package/2006/relationships"

def _excel_col_to_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n

def _col_letters(cell_ref: str) -> str:
    m = re.match(r"([A-Z]+)", cell_ref); return m.group(1) if m else cell_ref

def _load_shared_strings(z: zipfile.ZipFile) -> List[str]:
    try:
        xml = z.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    out = []
    for si in root.findall(f".//{{{_NS_MAIN}}}si"):
        out.append("".join(si.itertext()))
    return out

def _workbook_map(z: zipfile.ZipFile) -> Dict[str, str]:
    wb   = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    id_to_target = {}
    for rel in rels.findall(f".//{{{_NS_PKG}}}Relationship"):
        rid = rel.attrib.get("Id")
        tgt = rel.attrib.get("Target")
        if tgt and not tgt.startswith("xl/"): tgt = "xl/" + tgt
        id_to_target[rid] = tgt
    name_to_path = {}
    for s in wb.findall(f".//{{{_NS_MAIN}}}sheet"):
        name = s.attrib.get("name","").strip()
        rid  = s.attrib.get(f"{{{_NS_REL}}}id")
        path = id_to_target.get(rid)
        if name and path: name_to_path[name] = path
    return name_to_path

def _read_sheet(z: zipfile.ZipFile, sheet_path: str):
    return ET.fromstring(z.read(sheet_path))

def _col_widths(root) -> Dict[int, float]:
    widths = {}
    for c in root.findall(f".//{{{_NS_MAIN}}}col"):
        w = float(c.attrib.get("width", "0") or 0)
        if not w:
            continue
        min_i = int(c.attrib["min"]); max_i = int(c.attrib["max"])
        for idx in range(min_i, max_i + 1):
            widths[idx] = w
    return widths

def _first_rows(root, shared, max_rows=5) -> List[Dict[str, str]]:
    rows = []
    for row in root.findall(f".//{{{_NS_MAIN}}}row"):
        cells = {}
        for c in row.findall(f"./{{{_NS_MAIN}}}c"):
            ref = c.attrib.get("r","")
            t   = c.attrib.get("t")
            v   = c.find(f"./{{{_NS_MAIN}}}v")
            val = ""
            if t == "s":
                idx = int(v.text) if v is not None and v.text else 0
                val = shared[idx] if 0 <= idx < len(shared) else ""
            elif t == "inlineStr":
                is_el = c.find(f"./{{{_NS_MAIN}}}is")
                val = "".join(is_el.itertext()) if is_el is not None else ""
            else:
                val = v.text if v is not None else ""
            cells[ref] = (val or "").strip()
        if cells:
            rows.append(cells)
            if len(rows) >= max_rows:
                break
    return rows

def _guess_semantic_tag(header: str) -> Optional[str]:
    h = header.lower()
    if "proveedor" in h: return "proveedor"
    if "transport" in h or "tranportador" in h: return "transportista"
    if "receptor" in h: return "receptor"
    if "placa" in h or "placas" in h: return "placa"
    if "contenedor" in h: return "contenedor"
    if "precinto" in h or "sello" in h or "seal" in h: return "precinto"
    if "cédula" in h or "cedula" in h: return "documento"
    if "telefono" in h or "teléfono" in h: return "telefono"
    return "none"

def _guess_ui_hint(header: str) -> str:
    h = header.lower()
    if "hora" in h: return "time"
    if "fecha" in h: return "date"
    if "telefono" in h or "teléfono" in h: return "phone"
    return "text"

def _guess_type_and_file_mode(header: str) -> Tuple[str, Optional[str]]:
    # Dominio actual soporta "text" | "choice" | "file"
    h = header.lower()
    if "foto" in h or "imagen" in h or "evidencia" in h:
        return "file", "image_ocr"
    return "text", None

def _layout_path_for(qid) -> str:
    return f"questionnaire_layouts/{qid}.json"

class Command(BaseCommand):
    help = "Crea/actualiza un Questionnaire tabular a partir de un XLSX y guarda un layout JSON (anchos, headers)."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Ruta del archivo .xlsx")
        parser.add_argument("--title", type=str, help="Título del cuestionario (por defecto, nombre del archivo)")
        parser.add_argument("--qversion", "--q-version", dest="qversion", type=str, default="1.0",
                    help="Versión del Questionnaire (evita conflicto con --version global de Django)")
        parser.add_argument("--timezone", type=str, default="America/Bogota")
        parser.add_argument("--sheet", type=str, help="Nombre de hoja a usar (por defecto, primera hoja)")
        parser.add_argument("--truncate-questions", action="store_true",
            help="Borra preguntas existentes del cuestionario antes de insertar")
        parser.add_argument("--schema", type=str,
            help="Ruta a JSON con overrides por columna (type, required, semantic_tag, file_mode, ui_hint).")

    def handle(self, *args, **opts):
        path = opts["path"]
        if not os.path.exists(path):
            raise CommandError(f"No existe el archivo: {path}")
        try:
            z = zipfile.ZipFile(path)
        except Exception as e:
            raise CommandError(f"No pude abrir el XLSX: {e}")

        shared = _load_shared_strings(z)
        wb_map = _workbook_map(z)

        sheet = opts.get("sheet")
        if sheet:
            if sheet not in wb_map:
                raise CommandError(f"No encontré la hoja '{sheet}'. Disponibles: {', '.join(wb_map.keys())}")
            sheet_path = wb_map[sheet]
        else:
            if not wb_map:
                raise CommandError("El workbook no contiene hojas.")
            sheet, sheet_path = list(wb_map.items())[0]

        root = _read_sheet(z, sheet_path)
        widths_map = _col_widths(root)
        rows = _first_rows(root, shared, max_rows=10)

        if len(rows) < 2:
            raise CommandError("No se encontró una fila de cabecera clara (se espera encabezados en la fila 2).")

        headers_row = rows[1]   # en tu archivo, los encabezados están en la fila 2
        cols_letters = sorted({ _col_letters(ref) for ref in headers_row.keys() },
                              key=lambda s: [ord(ch) for ch in s])

        # carga overrides de schema opcional
        overrides = {}
        schema_file = opts.get("schema")
        if schema_file:
            with open(schema_file, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            overrides = (raw.get("columns") or {})

        title = (opts.get("title") or os.path.splitext(os.path.basename(path))[0]).strip()
        version = str(opts.get("qversion") or "1.0").strip()
        timezone = str(opts.get("timezone") or "America/Bogota").strip()

        self.stdout.write(self.style.NOTICE(f"Hoja: {sheet}. Columnas detectadas: {len(cols_letters)}"))

        layout_columns = []
        with transaction.atomic():
            qn, created = Questionnaire.objects.get_or_create(
                title=title, defaults={"version": version, "timezone": timezone}
            )
            if not created:
                upd = {}
                if qn.version != version: upd["version"] = version
                if qn.timezone != timezone: upd["timezone"] = timezone
                if upd: 
                    for k,v in upd.items(): setattr(qn, k, v)
                    qn.save(update_fields=list(upd.keys()))

            if opts.get("truncate_questions", False):
                qn.questions.all().delete()

            order = 1
            for col in cols_letters:
                ref = f"{col}2"
                header = headers_row.get(ref, "").strip()
                if not header:
                    continue

                inferred_type, inferred_file_mode = _guess_type_and_file_mode(header)
                inferred_tag = _guess_semantic_tag(header)
                ui_hint = _guess_ui_hint(header)
                required = False
                override = overrides.get(header) or overrides.get(header.strip())
                if override:
                    inferred_type = override.get("type", inferred_type)
                    inferred_file_mode = override.get("file_mode", inferred_file_mode)
                    inferred_tag = override.get("semantic_tag", inferred_tag)
                    ui_hint = override.get("ui_hint", ui_hint)
                    required = bool(override.get("required", False))

                # crear/actualizar question
                q = qn.questions.filter(text=header).first()
                if q:
                    changed = False
                    if q.type != inferred_type: q.type = inferred_type; changed = True
                    if q.required != required: q.required = required; changed = True
                    if q.order != order: q.order = order; changed = True
                    if (q.semantic_tag or None) != (inferred_tag or None): q.semantic_tag = inferred_tag or "none"; changed = True
                    if (q.file_mode or None) != (inferred_file_mode or None): q.file_mode = inferred_file_mode or ""; changed = True
                    if changed: q.save()
                else:
                    q = Question.objects.create(
                        id=uuid4(),
                        questionnaire=qn,
                        text=header,
                        type=inferred_type,
                        required=required,
                        order=order,
                        semantic_tag=inferred_tag or "none",
                        file_mode=inferred_file_mode or "",
                    )

                # layout visual
                width = widths_map.get(_excel_col_to_index(col))
                layout_columns.append({
                    "question_id": str(q.id),
                    "header": header,
                    "column": col,
                    "order": order,
                    "width": round(width, 2) if width else None,
                    "semantic_tag": inferred_tag or "none",
                    "ui_hint": ui_hint,
                })
                order += 1

            # guardar layout JSON en storage
            layout = {
                "questionnaire_id": str(qn.id),
                "title": qn.title,
                "version": qn.version,
                "timezone": qn.timezone,
                "columns": layout_columns,
            }
            path = _layout_path_for(qn.id)
            content = ContentFile(json.dumps(layout, ensure_ascii=False, indent=2).encode("utf-8"))
            if default_storage.exists(path):
                default_storage.delete(path)
            default_storage.save(path, content)

        self.stdout.write(self.style.SUCCESS(
            f"Cuestionario {'creado' if created else 'actualizado'}: '{qn.title}'. "
            f"Layout guardado en storage: {path}. Columnas: {len(layout_columns)}."
        ))
