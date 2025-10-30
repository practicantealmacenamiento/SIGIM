# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from django.db.models import Q

from app.domain.ports.repositories import ActorRepository
from app.infrastructure.models import Actor as ActorModel

class DjangoActorRepository(ActorRepository):
    """
    Repositorio para catálogo de actores (proveedor/transportista/receptor).
    Retorna modelos Django para uso directo con serializers manuales.
    """

    def get(self, id):
        try:
            obj = ActorModel.objects.get(id=id, activo=True)
            return obj
        except ActorModel.DoesNotExist:
            return None

    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50):
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
            # Fix typo: __icontincontains -> __icontains
            qs = qs.filter(Q(nombre__icontains=search) | Q(documento__icontains=search))
        return qs
