# -*- coding: utf-8 -*-
"""
app/infrastructure/storage.py
--------------------------------
Adaptador de almacenamiento para archivos usando el backend por defecto de Django.

Objetivos de diseño:
- Respetar el puerto de dominio `FileStorage` (clean architecture).
- Generar nombres seguros (UUID + extensión minúscula).
- Usar rutas POSIX ("/") para máxima compatibilidad (independiente de SO).
- Guardar en streaming (Django maneja los chunks).
- Traducir errores del backend a excepciones de dominio coherentes.
- Proveer utilidades seguras para obtener la URL protegida de media.

Puntos de extensión:
- Si en el futuro cambias el backend de storage (S3, GCS, etc.), bastará con
  inyectar otro `Storage` o implementar otro adaptador que cumpla con `FileStorage`.
"""

from __future__ import annotations

# ---- Dependencias estándar
import posixpath
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Union
from uuid import UUID

# ---- Django
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import Storage, default_storage
from django.urls import reverse

# ---- Dominio
from app.domain.ports.external_ports import FileStorage
from app.domain.exceptions import FileStorageError, InvalidFileError


# =============================================================================
# Adaptador principal: DjangoDefaultStorageAdapter
# =============================================================================
class DjangoDefaultStorageAdapter(FileStorage):
    """
    Implementación de `FileStorage` basada en `default_storage` de Django.

    - `save(folder=..., file_obj=...)` guarda el archivo y retorna el **path relativo**
      (e.g., "uploads/2025/10/17/uuid.ext").
    - `delete(path=...)` elimina el archivo de manera **idempotente** (si no existe, no falla).
    """

    def __init__(self, storage: Storage | None = None):
        """
        Constructor.

        Args:
            storage: Backend de Django a usar. Por defecto, `default_storage`.
        """
        self._storage = storage or default_storage

    # --------------------------------------------------------------------- #
    # API del puerto (save/delete)
    # --------------------------------------------------------------------- #
    def save(self, *, folder: str, file_obj) -> str:
        """
        Guarda un archivo en `folder` y devuelve su path relativo dentro del storage.

        Comportamiento:
        - Si `folder` está vacío, se crea una carpeta por fecha: "uploads/YYYY/MM/DD".
        - Se genera un nombre seguro `<uuid>.ext` manteniendo la extensión original en minúsculas.
        - El path resultante usa **separadores POSIX** ('/').

        Errores:
        - InvalidFileError: archivo vacío, nombre/ruta inválidos.
        - FileStorageError: error del backend (sistema de archivos, permisos, etc.).

        Returns:
            str: path relativo devuelto por el storage (e.g. "uploads/2025/10/17/abcd1234.png")
        """
        # 1) Validación temprana del archivo
        if not file_obj:
            raise InvalidFileError(message="Archivo vacío o no enviado.", file_name="unknown")

        try:
            if getattr(file_obj, "size", None) == 0:
                raise InvalidFileError(
                    message="Archivo vacío.",
                    file_name=getattr(file_obj, "name", "unknown"),
                    file_size=0,
                )
        except Exception:
            # Si no expone size, continuamos: el backend validará.
            pass

        try:
            # 2) Folder por defecto (fecha UTC) si no se especifica
            if not folder:
                today = datetime.now(timezone.utc)
                folder = f"uploads/{today.year:04d}/{today.month:02d}/{today.day:02d}"

            # 3) Sanitizar carpeta (defensivo contra rutas peligrosas)
            folder = self._validate_and_clean_folder(folder)

            # 4) Generar nombre seguro basado en UUID + extensión original
            original = getattr(file_obj, "name", "") or "file"
            ext = (Path(original).suffix or "").lower()  # ".png", ".jpg", ".pdf", etc.
            safe_name = f"{uuid.uuid4().hex}{ext}"

            # 5) Armar path POSIX relativo
            rel_path = posixpath.join(folder, safe_name)

            # 6) Asegurar que el puntero del archivo esté al inicio (si es seekable)
            try:
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)
            except Exception:
                # No es crítico si no logra hacer seek
                pass

            # 7) Guardar (Django maneja streaming/chunks internamente)
            saved_path = self._storage.save(rel_path, file_obj)

            if not saved_path:
                # El backend devolvió un path vacío: tratamos como error
                raise FileStorageError(
                    message="El storage devolvió un path vacío tras el guardado.",
                    storage_type=self._storage.__class__.__name__,
                    operation="save",
                    error_code="EMPTY_PATH",
                )

            return saved_path

        # --- Re-mapeo de errores a excepciones de dominio ----------------- #
        except InvalidFileError:
            # Si ya es InvalidFileError, no tocar.
            raise
        except SuspiciousOperation as e:
            # Rutas con caracteres peligrosos/invalidaciones de Django
            raise InvalidFileError(
                message=f"Ruta o nombre de archivo inválido: {e}",
                file_name=getattr(file_obj, "name", "unknown"),
            )
        except OSError as e:
            # Errores del sistema de archivos (permisos, disco, etc.)
            raise FileStorageError(
                message=f"Error del sistema de archivos: {e}",
                storage_type=self._storage.__class__.__name__,
                operation="save",
                error_code="OS_ERROR",
            )
        except Exception as e:
            # Cualquier otro error inesperado
            raise FileStorageError(
                message=f"Error inesperado guardando archivo: {e}",
                storage_type=self._storage.__class__.__name__,
                operation="save",
                error_code="SAVE_ERROR",
            )

    def delete(self, *, path: str) -> None:
        """
        Elimina un archivo del storage (operación **idempotente**).

        - Si `path` es vacío o el archivo no existe, no hace nada.
        - Si `path` es sospechoso (absoluto, backslashes, '..'), eleva `FileStorageError`.

        Args:
            path: Path relativo previamente devuelto por `save`.
        """
        if not path:
            return  # idempotente

        try:
            cleaned = self._validate_path_for_deletion(path)
            if self._storage.exists(cleaned):
                self._storage.delete(cleaned)

        # Seguridad: elevamos si el path es sospechoso o está mal formado
        except (SuspiciousOperation, FileStorageError):
            raise

        # Errores no críticos: mantenemos la idempotencia (silencioso),
        # aunque en un sistema real se podría registrar en logs/observabilidad.
        except Exception:
            pass

    # --------------------------------------------------------------------- #
    # Helpers internos (validación/sanitización de rutas)
    # --------------------------------------------------------------------- #
    def _validate_and_clean_folder(self, folder: str) -> str:
        """
        Valida y normaliza una carpeta **relativa** y segura.

        Reglas:
        - No permitir vacíos tras limpieza.
        - Bloquear `..`, backslashes y caracteres peligrosos.
        - Forzar separadores POSIX ('/').
        """
        if not folder or not isinstance(folder, str):
            raise InvalidFileError(
                message="La carpeta debe ser un string no vacío.",
                file_name="folder_validation",
            )

        # Quitar espacios y barras iniciales/finales
        folder = folder.strip().strip("/")

        if not folder:
            raise InvalidFileError(
                message="La carpeta es vacía tras normalizar.",
                file_name="folder_validation",
            )

        # Bloquear rutas peligrosas
        forbidden = ("..", "\\", "<", ">", ":", '"', "|", "?", "*")
        if folder.startswith("/") or any(ch in folder for ch in forbidden):
            raise InvalidFileError(
                message=f"Carpeta insegura: {folder}",
                file_name="folder_validation",
            )

        # Forzar POSIX (sin '.', sin vacíos)
        parts = [p for p in folder.split("/") if p and p != "."]
        safe = "/".join(parts)

        if not safe or safe.startswith("/"):
            raise InvalidFileError(
                message="Carpeta inválida tras limpieza.",
                file_name="folder_validation",
            )

        return safe

    def _validate_path_for_deletion(self, path: str) -> str:
        """
        Valida un path relativo antes de eliminar.

        Reglas:
        - Debe ser string no vacío.
        - Se limpia a POSIX y sin barra inicial.
        - No debe contener `..` ni backslashes.
        """
        if not path or not isinstance(path, str):
            raise FileStorageError(
                message="Path inválido para eliminación.",
                storage_type=self._storage.__class__.__name__,
                operation="delete",
                error_code="INVALID_PATH",
            )

        cleaned = path.strip().lstrip("/").replace("\\", "/")
        if not cleaned or ".." in cleaned or cleaned.startswith("/"):
            raise FileStorageError(
                message=f"Path peligroso: {path}",
                storage_type=self._storage.__class__.__name__,
                operation="delete",
                error_code="DANGEROUS_PATH",
            )
        return cleaned


# =============================================================================
# Utilidades públicas relacionadas
# =============================================================================
def get_secure_media_url(file_path: str) -> str:
    """
    Devuelve la **URL relativa** hacia el endpoint protegido `secure-media`
    para el `file_path` dado.

    Notas:
    - Asume que tienes en tu `urls.py` una named-url `"secure-media"` parecida a:
        path(f"{API_PREFIX}secure-media/<path:file_path>/", SecureMediaView.as_view(), name="secure-media")
    - Si `reverse()` falla (p.ej. nombre distinto), se hace un fallback defensivo.

    Args:
        file_path: Path relativo tal y como lo devolvió el storage (p. ej. "uploads/2025/10/17/uuid.png")

    Returns:
        str: URL relativa a tu endpoint protegido.
    """
    if not file_path:
        return ""
    # Normalizamos para evitar dobles barras o backslashes en URL
    safe = str(file_path).lstrip("/").replace("\\", "/")
    try:
        return reverse("secure-media", kwargs={"file_path": safe})
    except Exception:
        # Fallback defensivo — ajusta el prefijo si tu API tiene otro base path
        return f"/api/v1/secure-media/{safe}"


def _as_str_uuid(v: Union[str, UUID]) -> str:
    """
    Helper mínimo para convertir un valor a string (usado en logs/utilidades).
    """
    try:
        return str(v)
    except Exception:
        return f"{v}"
