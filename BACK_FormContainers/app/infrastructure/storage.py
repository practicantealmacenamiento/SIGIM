from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
import posixpath  # usar rutas POSIX en nombres de archivo (S3/local)
import os

from django.core.files.storage import default_storage
from django.core.files.storage import Storage
from django.core.exceptions import SuspiciousOperation

from app.domain.ports import FileStorage
from app.domain.exceptions import FileStorageError, InvalidFileError


class DjangoDefaultStorageAdapter(FileStorage):
    """
    Adapter de almacenamiento basado en Django default_storage.
    - Genera nombres seguros (UUID + extensión minúscula).
    - Retorna el path relativo guardado (con separadores '/').
    - Guarda en streaming (sin cargar todo a memoria).
    - Maneja errores específicos del servicio y traduce a excepciones de dominio.
    """

    def __init__(self, storage: Storage = None):
        """
        Initialize the storage adapter.
        
        Args:
            storage: Django storage backend to use. Defaults to default_storage.
        """
        self._storage = storage or default_storage

    def save(self, *, folder: str, file_obj) -> str:
        """
        Guarda un archivo y devuelve su 'path' relativo en el storage.
        
        Args:
            folder: Carpeta donde guardar el archivo
            file_obj: Objeto archivo a guardar
            
        Returns:
            str: Path relativo del archivo guardado
            
        Raises:
            InvalidFileError: Si el archivo es inválido
            FileStorageError: Si ocurre un error durante el almacenamiento
        """
        # Validar archivo
        if not file_obj:
            raise InvalidFileError(
                message="File object is None or empty",
                file_name="unknown"
            )

        # Validar que el archivo tenga contenido
        try:
            if hasattr(file_obj, 'size') and file_obj.size == 0:
                raise InvalidFileError(
                    message="File is empty",
                    file_name=getattr(file_obj, "name", "unknown"),
                    file_size=0
                )
        except Exception:
            # Si no podemos determinar el tamaño, continuamos
            pass

        try:
            # Carpeta por defecto si no viene una
            if not folder:
                today = datetime.now(timezone.utc)
                folder = f"uploads/{today.year:04d}/{today.month:02d}/{today.day:02d}"

            # Validar y limpiar folder
            folder = self._validate_and_clean_folder(folder)

            # Generar nombre seguro
            original_name = getattr(file_obj, "name", "upload")
            if not original_name:
                original_name = "upload"

            ext = (Path(original_name).suffix or "").lower()
            safe_name = f"{uuid.uuid4().hex}{ext}"

            # Usar POSIX join para asegurar barras '/'
            rel_path = posixpath.join(folder, safe_name)

            # Asegurar puntero al inicio si es seekable
            try:
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)
            except Exception:
                # Si no se puede hacer seek, continuamos
                pass

            # Guardar en streaming (Django maneja chunks internamente)
            saved_path = self._storage.save(rel_path, file_obj)
            
            if not saved_path:
                raise FileStorageError(
                    message="Storage returned empty path after save operation",
                    storage_type=self._storage.__class__.__name__,
                    operation="save"
                )
            
            return saved_path

        except InvalidFileError:
            # Re-raise domain exceptions as-is
            raise
        except SuspiciousOperation as e:
            raise InvalidFileError(
                message=f"Invalid file path or name: {str(e)}",
                file_name=getattr(file_obj, "name", "unknown")
            )
        except OSError as e:
            raise FileStorageError(
                message=f"File system error during save: {str(e)}",
                storage_type=self._storage.__class__.__name__,
                operation="save",
                error_code="OS_ERROR"
            )
        except Exception as e:
            raise FileStorageError(
                message=f"Unexpected error during file save: {str(e)}",
                storage_type=self._storage.__class__.__name__,
                operation="save",
                error_code="SAVE_ERROR"
            )

    def delete(self, *, path: str) -> None:
        """
        Elimina un archivo del storage (idempotente).
        
        Args:
            path: Path del archivo a eliminar
            
        Raises:
            FileStorageError: Si ocurre un error crítico durante la eliminación
        """
        if not path:
            # Operación idempotente - no hacer nada si no hay path
            return

        try:
            # Validar que el path no sea sospechoso
            cleaned_path = self._validate_path_for_deletion(path)
            
            # Intentar eliminar el archivo
            if self._storage.exists(cleaned_path):
                self._storage.delete(cleaned_path)
                
        except SuspiciousOperation as e:
            raise FileStorageError(
                message=f"Invalid file path for deletion: {str(e)}",
                storage_type=self._storage.__class__.__name__,
                operation="delete",
                error_code="SUSPICIOUS_PATH"
            )
        except OSError as e:
            # Para errores del sistema de archivos, solo logueamos pero no fallamos
            # ya que delete debe ser idempotente
            pass
        except Exception as e:
            # Para otros errores inesperados, también los manejamos silenciosamente
            # para mantener la idempotencia, pero podríamos loguear en un sistema real
            pass

    def _validate_and_clean_folder(self, folder: str) -> str:
        """
        Valida y limpia el nombre de la carpeta.
        
        Args:
            folder: Nombre de carpeta a validar
            
        Returns:
            str: Carpeta limpia y validada
            
        Raises:
            InvalidFileError: Si la carpeta es inválida
        """
        if not folder or not isinstance(folder, str):
            raise InvalidFileError(
                message="Folder name must be a non-empty string",
                file_name="folder_validation"
            )

        # Limpiar la carpeta
        folder = folder.strip("/").strip()
        
        if not folder:
            raise InvalidFileError(
                message="Folder name cannot be empty after cleaning",
                file_name="folder_validation"
            )

        # Validar caracteres peligrosos
        dangerous_chars = ['..', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in folder:
                raise InvalidFileError(
                    message=f"Folder name contains dangerous character: {char}",
                    file_name=folder
                )

        return folder

    def _validate_path_for_deletion(self, path: str) -> str:
        """
        Valida un path para operaciones de eliminación.
        
        Args:
            path: Path a validar
            
        Returns:
            str: Path validado
            
        Raises:
            FileStorageError: Si el path es inválido o peligroso
        """
        if not path or not isinstance(path, str):
            raise FileStorageError(
                message="Path must be a non-empty string",
                storage_type=self._storage.__class__.__name__,
                operation="delete",
                error_code="INVALID_PATH"
            )

        # Limpiar el path
        cleaned_path = path.strip()
        
        if not cleaned_path:
            raise FileStorageError(
                message="Path cannot be empty after cleaning",
                storage_type=self._storage.__class__.__name__,
                operation="delete",
                error_code="EMPTY_PATH"
            )

        # Validar que no sea un path peligroso
        if cleaned_path.startswith('/') or '\\' in cleaned_path or '..' in cleaned_path:
            raise FileStorageError(
                message=f"Dangerous path detected: {cleaned_path}",
                storage_type=self._storage.__class__.__name__,
                operation="delete",
                error_code="DANGEROUS_PATH"
            )

        return cleaned_path

