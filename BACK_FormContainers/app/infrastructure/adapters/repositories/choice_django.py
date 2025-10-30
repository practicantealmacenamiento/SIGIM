# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.domain.entities import Choice as DC
from app.domain.ports.repositories import ChoiceRepository
from app.infrastructure.models import Choice as ChoiceModel

class DjangoChoiceRepository(ChoiceRepository):
    """Repositorio mínimo de opciones de pregunta."""

    def get(self, id: UUID) -> Optional[DC]:
        model = ChoiceModel.objects.filter(id=id).only("id", "text", "branch_to").first()
        return self._model_to_entity(model) if model else None

    def _model_to_entity(self, model: ChoiceModel) -> DC:
        return DC(id=model.id, text=model.text, branch_to=model.branch_to_id)
