# -*- coding: utf-8 -*-
"""
Adaptadores de infraestructura (Django) para puertos del dominio.

Incluye:
- DjangoTransactionAdapter: implementación del método `atomic()` usando `django.db.transaction.atomic`.

Cuándo usar este archivo
------------------------
Úsalo si tu capa de aplicación expone/consume un puerto de transacciones (p. ej. `TransactionPort`)
para delimitar unidades de trabajo atómicas alrededor de casos de uso (comandos que afectan varias tablas).

Si tu aplicación NO define ni usa un puerto de transacciones:
- Este archivo es opcional y puedes eliminarlo sin afectar otras piezas.
- Alternativamente, puedes mantenerlo como helper ligero (`use_transaction`) para scopes atómicos.

Notas:
- No introduce dependencias en la capa de dominio (sólo intenta tipar con el puerto si existe).
- No añade lógica de negocio; sólo expone `atomic()` como adaptador.
"""

from __future__ import annotations

# ── Stdlib ─────────────────────────────────────────────────────────────────────
from typing import ContextManager, Protocol

# ── Django ─────────────────────────────────────────────────────────────────────
from django.db import transaction

# ── Tipado opcional del puerto ─────────────────────────────────────────────────
try:
    # Si existe el puerto en dominio, lo importamos para chequear contrato.
    # En algunos proyectos no está definido; en tal caso tipamos localmente.
    from app.domain.ports import TransactionPort  # type: ignore
except Exception:  # pragma: no cover - fallback de tipado
    class TransactionPort(Protocol):
        """Contrato mínimo esperado para un puerto de transacciones."""
        def atomic(self) -> ContextManager[None]:  # noqa: D401
            """Devuelve un context manager transaccional."""
            ...


class DjangoTransactionAdapter(TransactionPort):
    """
    Implementación del puerto de transacciones usando Django.

    Uso:
        tx = DjangoTransactionAdapter()
        with tx.atomic():
            # operaciones de aplicación/infra que deben ser atómicas
            ...

    Detalles:
        - Delegamos directamente en `transaction.atomic()` de Django.
        - No añadimos lógica adicional (savepoints, retries, etc.).
    """

    def atomic(self) -> ContextManager[None]:
        """Context manager transaccional de Django (atomic)."""
        return transaction.atomic()


def use_transaction() -> ContextManager[None]:
    """
    Helper de conveniencia cuando no necesitas instanciar el adaptador.

    Uso:
        with use_transaction():
            ...

    Equivalente a `transaction.atomic()`.
    """
    return transaction.atomic()


__all__ = [
    "DjangoTransactionAdapter",
    "use_transaction",
]
