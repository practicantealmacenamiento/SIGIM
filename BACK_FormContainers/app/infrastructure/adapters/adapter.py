# app/infrastructure/adapters/adapters.py
"""
Adaptadores de infraestructura (Django, etc.) para puertos del dominio.

Incluye:
- DjangoTransactionAdapter: implementación de TransactionPort usando transaction.atomic()

Nota: Otros adaptadores (storage, colas, cache) pueden agregarse aquí siguiendo el mismo patrón.
"""

from __future__ import annotations

from typing import ContextManager
from django.db import transaction

from app.domain.ports import TransactionPort


class DjangoTransactionAdapter(TransactionPort):
    """
    Implementa el puerto de transacciones usando Django.
    Uso:
        tx = DjangoTransactionAdapter()
        with tx.atomic():
            ... # operaciones de aplicación/infra
    """

    def atomic(self) -> ContextManager[None]:
        return transaction.atomic()


__all__ = [
    "DjangoTransactionAdapter",
]
