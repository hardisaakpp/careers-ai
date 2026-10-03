"""Modelo de la hoja de vida: la fuente de verdad es el dato, no el documento."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contacto(_Base):
    email: str
    telefono: str | None = None
    ubicacion: str | None = None
    enlaces: dict[str, str] = Field(default_factory=dict)


class Experiencia(_Base):
    cargo: str
    organizacion: str
    desde: str
    hasta: str | None = None  # None = actual
    logros: list[str] = Field(default_factory=list)
    tecnologias: list[str] = Field(default_factory=list)


class Educacion(_Base):
    titulo: str
    institucion: str
    desde: str
    hasta: str | None = None


class Proyecto(_Base):
    nombre: str
    descripcion: str
    url: str | None = None
    tecnologias: list[str] = Field(default_factory=list)


class GrupoHabilidades(_Base):
    nombre: str
    items: list[str]


class Cv(_Base):
    nombre: str
    titular: str
    resumen: str
    contacto: Contacto
    experiencia: list[Experiencia] = Field(default_factory=list)
    proyectos: list[Proyecto] = Field(default_factory=list)
    educacion: list[Educacion] = Field(default_factory=list)
    habilidades: list[GrupoHabilidades] = Field(default_factory=list)

    def tecnologias(self) -> set[str]:
        """Todas las tecnologías declaradas: base para comparar con ofertas."""
        vistas: set[str] = set()
        for e in self.experiencia:
            vistas.update(e.tecnologias)
        for p in self.proyectos:
            vistas.update(p.tecnologias)
        for g in self.habilidades:
            vistas.update(g.items)
        return vistas
