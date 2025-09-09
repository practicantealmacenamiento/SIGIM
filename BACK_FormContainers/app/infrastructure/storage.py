from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
import posixpath  # usar rutas POSIX en nombres de archivo (S3/local)

from django.core.files.storage import default_storage

from app.domain.ports import FileStorage


class DjangoDefaultStorageAdapter(FileStorage):
    """
    Adapter de almacenamiento basado en Django default_storage.
    - Genera nombres seguros (UUID + extensión minúscula).
    - Retorna el path relativo guardado (con separadores '/').
    - Guarda en streaming (sin cargar todo a memoria).
    """

    def save(self, *, folder: str, file_obj) -> str:
        # Carpeta por defecto si no viene una
        if not folder:
            today = datetime.now(timezone.utc)
            folder = f"uploads/{today.year:04d}/{today.month:02d}/{today.day:02d}"

        original_name = getattr(file_obj, "name", "upload")
        ext = (Path(original_name).suffix or "").lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"

        # Usar POSIX join para asegurar barras '/'
        folder = folder.strip("/")

        rel_path = posixpath.join(folder, safe_name)

        # Asegurar puntero al inicio si es seekable
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        except Exception:
            pass

        # Guardar en streaming (Django maneja chunks internamente)
        saved_path = default_storage.save(rel_path, file_obj)
        return saved_path

    def delete(self, *, path: str) -> None:
        try:
            default_storage.delete(path)
        except Exception:
            # Idempotente / best-effort
            pass

