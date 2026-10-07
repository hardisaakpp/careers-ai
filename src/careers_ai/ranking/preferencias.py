from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Preferencias(BaseModel):
    """Reglas duras: lo que descarta una oferta sin importar su afinidad."""

    model_config = ConfigDict(extra="forbid")

    excluir_titulos: list[str] = Field(default_factory=list)  # p. ej. "sales", "recruiter"
    excluir_texto: list[str] = Field(default_factory=list)    # p. ej. "security clearance"
    ubicaciones: list[str] = Field(default_factory=list)      # vacío = cualquiera
    obligatorias: list[str] = Field(default_factory=list)     # tecnologías imprescindibles
    # Años de experiencia que la persona tiene o está dispuesta a aceptar como máximo en una oferta (None = sin límite).
    max_anos: int | None = Field(default=None, ge=0, le=30)
