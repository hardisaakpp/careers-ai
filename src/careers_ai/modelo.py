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
    ubicacion: str | None = None
    logros: list[str] = Field(default_factory=list)
    tecnologias: list[str] = Field(default_factory=list)
    incluir: bool = True  # False = se guarda pero no sale en el PDF


class Educacion(_Base):
    titulo: str
    institucion: str
    desde: str
    hasta: str | None = None
    ubicacion: str | None = None
    incluir: bool = True


class Proyecto(_Base):
    nombre: str
    descripcion: str
    url: str | None = None
    tecnologias: list[str] = Field(default_factory=list)
    incluir: bool = True


class Certificacion(_Base):
    nombre: str
    emisor: str = ""
    anio: str = ""
    incluir: bool = True


class Idioma(_Base):
    nombre: str
    nivel: str = ""
    incluir: bool = True


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
    # Investigación tiene la misma forma que un trabajo (cargo, laboratorio, fechas, logros).
    investigacion: list[Experiencia] = Field(default_factory=list)
    certificaciones: list[Certificacion] = Field(default_factory=list)
    idiomas: list[Idioma] = Field(default_factory=list)
    # Qué NO sale en el PDF: secciones ("resumen", "experiencia", …) y datos de contacto
    # ("contacto.telefono", …). Vacío = todo lo recomendado. Lo guardado nunca se pierde.
    ocultas: list[str] = Field(default_factory=list)

    def para_pdf(self) -> "Cv":
        """Copia con solo lo que el usuario quiere en el PDF; el original no se toca."""
        def visible(clave: str) -> bool:
            return clave not in self.ocultas

        def usar(items):
            return [i for i in items if i.incluir]

        contacto = self.contacto.model_copy(update={
            "telefono": self.contacto.telefono if visible("contacto.telefono") else None,
            "ubicacion": self.contacto.ubicacion if visible("contacto.ubicacion") else None,
            "enlaces": self.contacto.enlaces if visible("contacto.enlaces") else {},
        })
        return self.model_copy(update={
            "resumen": self.resumen if visible("resumen") else "",
            "contacto": contacto,
            "experiencia": usar(self.experiencia) if visible("experiencia") else [],
            "investigacion": usar(self.investigacion) if visible("investigacion") else [],
            "proyectos": usar(self.proyectos) if visible("proyectos") else [],
            "educacion": usar(self.educacion) if visible("educacion") else [],
            "habilidades": self.habilidades if visible("habilidades") else [],
            "certificaciones": usar(self.certificaciones) if visible("certificaciones") else [],
            "idiomas": usar(self.idiomas) if visible("idiomas") else [],
        })

    def tecnologias(self) -> set[str]:
        """Todas las tecnologías declaradas: base para comparar con ofertas."""
        vistas: set[str] = set()
        for e in [*self.experiencia, *self.investigacion]:
            vistas.update(e.tecnologias)
        for p in self.proyectos:
            vistas.update(p.tecnologias)
        for g in self.habilidades:
            vistas.update(g.items)
        return vistas
