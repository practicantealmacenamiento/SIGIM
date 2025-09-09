# app/infrastructure/management/commands/dedup_actores.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
import unicodedata, re
from typing import Tuple, Dict, List

# Ajusta este import si tus modelos viven en otro app
from app.infrastructure.models import Actor, Submission

def strip_accents(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def normalize_name(s: str) -> str:
    """
    Normaliza nombre para comparar:
    - casefold (mayús/minus)
    - quita acentos
    - colapsa espacios
    - elimina símbolos/puntuación (deja letras y números)
    """
    s = (s or "").casefold()
    s = strip_accents(s)
    s = " ".join(s.split())
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def normalize_doc(s: str) -> str:
    """Documento sin espacios ni símbolos, mayúsculas."""
    s = (s or "").strip().upper()
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def pretty_name(s: str) -> str:
    """Limpia visual (colapsa espacios) sin perder mayúsculas originales."""
    return " ".join((s or "").split())

def actor_key(a: Actor) -> Tuple[str, str, str]:
    """
    Devuelve (tipo, clave_tipo, clave_valor)
    - Si hay documento: ('doc', DOC_NORMALIZADO)
    - Si no hay:        ('name', NOMBRE_NORMALIZADO)
    """
    if a.documento and a.documento.strip():
        return (a.tipo, "doc", normalize_doc(a.documento))
    return (a.tipo, "name", normalize_name(a.nombre))

class Command(BaseCommand):
    help = "Deduplica Actor por tipo+documento o tipo+nombre normalizado, reasignando Submissions y borrando duplicados."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Ejecuta cambios (por defecto es dry-run).")
        parser.add_argument("--limit", type=int, default=0, help="Procesa a lo sumo N grupos (0 = todos).")
        parser.add_argument("--fix-canonical-name", action="store_true",
                            help="Limpia nombre del canónico (colapsa espacios).")

    def handle(self, *args, **opts):
        dry_run = not opts["commit"]
        limit = int(opts.get("limit") or 0)
        fix_canonical = bool(opts.get("fix_canonical_name"))

        qs = Actor.objects.all().order_by("tipo", "nombre", "id")
        total = qs.count()
        self.stdout.write(self.style.NOTICE(f"Actores totales: {total}"))

        # 1) Agrupar por clave
        buckets: Dict[Tuple[str, str, str], List[Actor]] = {}
        for a in qs:
            k = actor_key(a)
            buckets.setdefault(k, []).append(a)

        # 2) Filtrar solo grupos con más de 1 (duplicados potenciales)
        groups = [(k, v) for k, v in buckets.items() if len(v) > 1]
        groups.sort(key=lambda kv: (-len(kv[1]), kv[0]))  # primero los más grandes

        if limit > 0:
            groups = groups[:limit]

        self.stdout.write(self.style.NOTICE(f"Grupos con posibles duplicados: {len(groups)}"))

        # Estadísticas
        total_dups = 0
        total_sub_updates = 0
        total_deleted = 0

        # 3) Procesar grupos
        for (tipo, kind, keyval), actors in groups:
            # Elegir canónico:
            # - Prefiere con documento
            # - Si no, el nombre más largo (más informativo)
            with_doc = [a for a in actors if (a.documento or "").strip()]
            if with_doc:
                canonical = with_doc[0]
            else:
                canonical = max(actors, key=lambda x: len((x.nombre or "").strip()))

            losers = [a for a in actors if a.id != canonical.id]
            total_dups += len(losers)

            self.stdout.write(self.style.WARNING(
                f"[{tipo}:{kind}:{keyval}] → canónico: {canonical.id} '{canonical.nombre}' "
                f"(dups: {len(losers)})"
            ))

            # 4) Reasignar Submissions
            #   Campos en Submission (según tu código): proveedor_id, transportista_id, receptor_id
            where_prov = Q(proveedor_id__in=[x.id for x in losers])
            where_trans = Q(transportista_id__in=[x.id for x in losers])
            where_rec = Q(receptor_id__in=[x.id for x in losers])

            updates = 0
            if not dry_run:
                with transaction.atomic():
                    if tipo == Actor.Tipo.PROVEEDOR:
                        updates += Submission.objects.filter(where_prov).update(proveedor_id=canonical.id)
                    elif tipo == Actor.Tipo.TRANSPORTISTA:
                        updates += Submission.objects.filter(where_trans).update(transportista_id=canonical.id)
                    elif tipo == Actor.Tipo.RECEPTOR:
                        updates += Submission.objects.filter(where_rec).update(receptor_id=canonical.id)
                    else:
                        # Por si en un futuro hay más tipos, intentamos reasignar en los 3 campos
                        updates += Submission.objects.filter(where_prov).update(proveedor_id=canonical.id)
                        updates += Submission.objects.filter(where_trans).update(transportista_id=canonical.id)
                        updates += Submission.objects.filter(where_rec).update(receptor_id=canonical.id)

                    # (Opcional) Limpia nombre del canónico
                    if fix_canonical:
                        new_name = pretty_name(canonical.nombre)
                        if new_name != canonical.nombre:
                            Actor.objects.filter(id=canonical.id).update(nombre=new_name)

                    # Borrar duplicados
                    Actor.objects.filter(id__in=[x.id for x in losers]).delete()

            total_sub_updates += updates
            total_deleted += len(losers)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY-RUN: no se hicieron cambios.\n"
                                                 "Ejecuta con --commit para aplicar."))
        self.stdout.write(self.style.SUCCESS(
            f"\nResumen: grupos={len(groups)} duplicados={total_dups} "
            f"submissions_reasignadas={total_sub_updates} eliminados={total_deleted}"
        ))
