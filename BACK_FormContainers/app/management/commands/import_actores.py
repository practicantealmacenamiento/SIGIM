import re, zipfile, xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from app.infrastructure.models import Actor

# ========= util XLSX (sin libs externas) =========
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG  = "http://schemas.openxmlformats.org/package/2006/relationships"

def _col_letters(cell_ref: str) -> str:
    m = re.match(r"([A-Z]+)", cell_ref); return m.group(1) if m else cell_ref

def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    try: xml = z.read("xl/sharedStrings.xml")
    except KeyError: return []
    root = ET.fromstring(xml); out=[]
    for si in root.findall(f".//{{{_NS_MAIN}}}si"):
        out.append("".join(si.itertext()))
    return out

def _workbook_map(z: zipfile.ZipFile) -> dict[str, str]:
    wb   = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    id_to_target={}
    for rel in rels.findall(f".//{{{_NS_PKG}}}Relationship"):
        rid = rel.attrib.get("Id"); tgt = rel.attrib.get("Target")
        if tgt and not tgt.startswith("xl/"): tgt = "xl/" + tgt
        id_to_target[rid] = tgt
    name_to_path={}
    for s in wb.findall(f".//{{{_NS_MAIN}}}sheet"):
        name = s.attrib.get("name","").strip()
        rid  = s.attrib.get(f"{{{_NS_REL}}}id")
        path = id_to_target.get(rid)
        if name and path: name_to_path[name] = path
    return name_to_path

def _read_sheet_rows(z: zipfile.ZipFile, sheet_path: str, shared: list[str]):
    """
    Devuelve (headers:list[str], rows:list[dict])
    Cabecera = fila 1. Las filas vacías se descartan.
    """
    root = ET.fromstring(z.read(sheet_path))
    rows=[]; header_map=None
    for row in root.findall(f".//{{{_NS_MAIN}}}row"):
        cells={}
        for c in row.findall(f"./{{{_NS_MAIN}}}c"):
            ref = c.attrib.get("r",""); col = _col_letters(ref)
            t   = c.attrib.get("t"); v_el = c.find(f"./{{{_NS_MAIN}}}v")
            text=""
            if t == "s":
                idx = int(v_el.text) if v_el is not None and v_el.text else 0
                text = shared[idx] if 0 <= idx < len(shared) else ""
            elif t == "inlineStr":
                is_el = c.find(f"./{{{_NS_MAIN}}}is")
                text = "".join(is_el.itertext()) if is_el is not None else ""
            else:
                text = v_el.text if v_el is not None and v_el.text is not None else ""
            cells[col] = (text or "").strip()
        if not cells: continue

        if header_map is None:
            cols_sorted = sorted(cells.keys(), key=lambda x: [ord(ch) for ch in x])
            header_map = {col: (cells[col] or "").strip() for col in cols_sorted if cells.get(col)}
            continue

        row_dict = { header_map[col]: cells.get(col, "") for col in header_map.keys() }
        if any(v for v in row_dict.values()):
            rows.append(row_dict)
    headers = list(header_map.values()) if header_map else []
    return headers, rows

# ========= normalizadores / upsert =========
def _norm_name(s: str) -> str:
    s = (s or "").replace("\t"," ").strip()
    s = re.sub(r"\s+", " ", s)
    return s

@transaction.atomic
def _upsert_list(tipo: str, items: list[dict], nombre_key: str, observ_key: str|None=None):
    new = upd = 0
    for r in items:
        nombre = _norm_name(r.get(nombre_key, ""))
        if not nombre:
            continue
        # Upsert por (tipo, nombre iexact) – no hay 'documento' en tu archivo
        obj = Actor.objects.filter(tipo=tipo, nombre__iexact=nombre).first()
        if obj:
            # actualiza meta.observacion si aplica
            if observ_key and r.get(observ_key):
                meta = dict(obj.meta or {})
                meta["observacion"] = str(r.get(observ_key)).strip()
                if meta != obj.meta:
                    obj.meta = meta; obj.save(update_fields=["meta"])
            upd += 1
        else:
            meta = {}
            if observ_key and r.get(observ_key):
                meta["observacion"] = str(r.get(observ_key)).strip()
            Actor.objects.create(tipo=tipo, nombre=nombre, documento=None, activo=True, meta=meta)
            new += 1
    return new, upd

# ========= comando =========
class Command(BaseCommand):
    help = "Importa Proveedores, Transportistas y Usuarios de Recibo desde un único .xlsx (sin librerías externas)."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Ruta del archivo .xlsx")
        # Nombres de hojas esperados (ajustados a tu archivo)
        parser.add_argument("--sheet-proveedores", type=str, default="Proveedores")
        parser.add_argument("--sheet-transportadores", type=str, default="Transportadores")
        parser.add_argument("--sheet-receptores", type=str, default="Usuarios de Recibo")
        # Modo dry-run
        parser.add_argument("--dry-run", action="store_true", help="Solo parsea y muestra conteos; no escribe en DB")

    def handle(self, *args, **opts):
        path = opts["path"]
        try:
            z = zipfile.ZipFile(path)
        except Exception as e:
            raise CommandError(f"No pude abrir el XLSX: {e}")

        shared = _load_shared_strings(z)
        wb_map = _workbook_map(z)

        # Resolver paths de hojas (admite pequeñas variaciones en Receptores)
        prov_sheet = opts["sheet_proveedores"].strip()
        trans_sheet = opts["sheet_transportadores"].strip()
        recv_sheet = opts["sheet_receptores"].strip()
        if prov_sheet not in wb_map:
            raise CommandError(f"No encontré la hoja '{prov_sheet}'")
        if trans_sheet not in wb_map:
            raise CommandError(f"No encontré la hoja '{trans_sheet}'")
        if recv_sheet not in wb_map:
            # tolera variaciones típicas
            for alt in ("Usuarios de Recibo", "Usuarios de recibo", "Usuarios de recibo "):
                if alt in wb_map: recv_sheet = alt; break
            if recv_sheet not in wb_map:
                raise CommandError(f"No encontré la hoja de receptores '{opts['sheet_receptores']}'")

        # Leer hojas
        prov_hdrs, prov_rows = _read_sheet_rows(z, wb_map[prov_sheet], shared)
        trans_hdrs, trans_rows = _read_sheet_rows(z, wb_map[trans_sheet], shared)
        rec_hdrs, rec_rows = _read_sheet_rows(z, wb_map[recv_sheet], shared)

        # Mapear encabezados reales de tu archivo
        # Proveedores: columna 'Proveedor'
        prov_name_col = "Proveedor" if "Proveedor" in prov_hdrs else prov_hdrs[0]
        # Transportadores: columna 'TRANSPORTADOR Y PROVEEDOR'
        trans_name_col = "TRANSPORTADOR Y PROVEEDOR" if "TRANSPORTADOR Y PROVEEDOR" in trans_hdrs else trans_hdrs[0]
        # Receptores: columnas 'Nombre' y 'Observacion'
        rec_name_col = "Nombre" if "Nombre" in rec_hdrs else rec_hdrs[0]
        rec_obs_col  = "Observacion" if "Observacion" in rec_hdrs else (rec_hdrs[1] if len(rec_hdrs)>1 else None)

        self.stdout.write(self.style.NOTICE(
            f"Detectado: Proveedores={len(prov_rows)}, Transportadores={len(trans_rows)}, Receptores={len(rec_rows)}"
        ))

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run OK. No se realizó escritura en BD."))
            return

        n1,u1 = _upsert_list(Actor.Tipo.PROVEEDOR,     prov_rows, prov_name_col)
        n2,u2 = _upsert_list(Actor.Tipo.TRANSPORTISTA, trans_rows, trans_name_col)
        n3,u3 = _upsert_list(Actor.Tipo.RECEPTOR,      rec_rows,  rec_name_col, observ_key=rec_obs_col)

        self.stdout.write(self.style.SUCCESS(
            f"Importación completa. Nuevos: {n1+n2+n3} (Prov {n1}, Transp {n2}, Recept {n3}) | "
            f"Actualizados: {u1+u2+u3}"
        ))
        