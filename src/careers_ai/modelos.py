"""Oferta tal como llega a este servicio: sin identidad propia, solo lo necesario para juzgarla.

El texto es de terceros y no se confía en él: nada aquí lo interpreta como instrucciones.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Oferta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(max_length=64)  # lo asigna quien llama; se devuelve tal cual
    titulo: str = Field(max_length=300)
    empresa: str = Field(default="", max_length=300)
    ubicacion: str = Field(default="", max_length=500)
    etiquetas: list[str] = Field(default_factory=list, max_length=40)
    descripcion: str = Field(default="", max_length=12000)
