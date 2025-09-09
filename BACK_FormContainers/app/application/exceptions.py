from dataclasses import dataclass


@dataclass(eq=False)
class DomainError(Exception):
    """Error base de dominio (capa domain)."""
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class ValidationError(DomainError):
    """Errores de validación de entidades/VOs."""
    pass