from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol


# ---- Puerto tecnológico: OCR/Text Extraction ----
class TextExtractorPort(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """Devuelve el texto extraído desde bytes de imagen."""
        ...


# ---- Puerto tecnológico: File Storage ----
class FileStorage(Protocol):
    """
    Puerto para almacenamiento de archivos.
    Retorna la ruta relativa (name) persistida por el storage.
    """

    def save(self, *, folder: str, file_obj) -> str:
        """Guarda un archivo y devuelve su 'path' relativo en el storage."""
        ...

    def delete(self, *, path: str) -> None:
        """Elimina un archivo del storage (idempotente)."""
        ...
