"""El ZIP de «Obtener una copia de tus datos» de LinkedIn → borrador de hoja de vida.

Los CSV ya vienen estructurados: no se interpreta nada, solo se acomoda. Es la vía más exacta.
Los nombres de archivo y de columna se buscan sin distinguir mayúsculas y los que falten se omiten:
LinkedIn los cambia de vez en cuando y el ZIP trae mucho más de lo que una hoja de vida necesita.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile

from ..modelo import Certificacion, Contacto, Cv, Educacion, Experiencia, GrupoHabilidades, Idioma
from .errores import ImportacionError

MAX_ARCHIVOS = 300
MAX_CSV = 5 * 1024 * 1024
NOMBRES = {"profile", "positions", "education", "skills", "certifications", "languages",
           "email addresses", "phonenumbers"}


def _csvs(z: zipfile.ZipFile) -> dict[str, list[dict[str, str]]]:
    """Filas por nombre de archivo (sin ruta ni extensión, en minúsculas); solo los CSV que interesan."""
    infos = z.infolist()
    if len(infos) > MAX_ARCHIVOS:
        raise ImportacionError("zip-sin-datos")
    salida: dict[str, list[dict[str, str]]] = {}
    for info in infos:
        nombre = info.filename.rsplit("/", 1)[-1]
        if not nombre.lower().endswith(".csv"):
            continue
        clave = nombre[:-4].lower()
        if clave not in NOMBRES:
            continue
        if info.file_size > MAX_CSV:
            raise ImportacionError("demasiado-grande")
        texto = z.read(info).decode("utf-8-sig", errors="replace")
        salida[clave] = _filas(texto)
    return salida


# Columnas que se leen: el encabezado es la primera línea que trae alguna (los archivos de una sola
# columna, como Skills.csv, no tienen comas, y algunos traen notas antes del encabezado).
COLUMNAS = {"name", "first name", "company name", "school name", "email address", "number"}


def _filas(texto: str) -> list[dict[str, str]]:
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        celdas = next(csv.reader([linea]), [])
        if COLUMNAS & {c.strip().lower() for c in celdas}:
            lector = csv.DictReader(io.StringIO("\n".join(lineas[i:])))
            return [{(k or "").strip().lower(): (v or "").strip() for k, v in fila.items()} for fila in lector]
    return []


def _col(fila: dict[str, str], *nombres: str) -> str:
    for n in nombres:
        if fila.get(n):
            return fila[n]
    return ""


def _logros(descripcion: str) -> list[str]:
    """Una viñeta por línea; si es un solo párrafo, queda como un único logro."""
    partes = re.split(r"\n+|\s*[•·▪●]\s*", descripcion)
    return [p.strip(" -–—*\t") for p in partes if p.strip(" -–—*\t")]


def desde_zip(datos: bytes) -> tuple[Cv, list[str]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile as e:
        raise ImportacionError("ilegible") from e
    with z:
        tablas = _csvs(z)
    if not any(k in tablas for k in ("profile", "positions", "education")):
        raise ImportacionError("zip-sin-datos")

    perfil = (tablas.get("profile") or [{}])[0]
    nombre = " ".join(p for p in (_col(perfil, "first name"), _col(perfil, "last name")) if p)
    correos = tablas.get("email addresses", [])
    primario = next((c for c in correos if c.get("primary", "").lower() == "yes"), correos[0] if correos else {})
    telefonos = tablas.get("phonenumbers", [])
    sitios = [s.strip() for s in re.split(r"[,\n]", _col(perfil, "websites")) if s.strip().startswith("http")]

    experiencia = [
        Experiencia(
            cargo=_col(f, "title"), organizacion=_col(f, "company name"),
            desde=_col(f, "started on"), hasta=_col(f, "finished on") or None,
            ubicacion=_col(f, "location") or None, logros=_logros(_col(f, "description")),
        )
        for f in tablas.get("positions", []) if _col(f, "title", "company name")
    ]
    educacion = [
        Educacion(
            titulo=_col(f, "degree name") or _col(f, "school name"), institucion=_col(f, "school name"),
            desde=_col(f, "start date"), hasta=_col(f, "end date") or None,
        )
        for f in tablas.get("education", []) if _col(f, "school name", "degree name")
    ]
    habilidades = [_col(f, "name") for f in tablas.get("skills", []) if _col(f, "name")]
    cv = Cv(
        nombre=nombre, titular=_col(perfil, "headline"), resumen=_col(perfil, "summary"),
        contacto=Contacto(
            email=_col(primario, "email address"),
            telefono=_col(telefonos[0], "number") or None if telefonos else None,
            ubicacion=_col(perfil, "geo location", "address") or None,
            enlaces={f"Sitio {i + 1}" if len(sitios) > 1 else "Sitio web": u for i, u in enumerate(sitios)},
        ),
        experiencia=experiencia, educacion=educacion,
        habilidades=[GrupoHabilidades(nombre="Habilidades", items=habilidades)] if habilidades else [],
        certificaciones=[
            Certificacion(nombre=_col(f, "name"), emisor=_col(f, "authority"),
                          anio=(_col(f, "started on") or _col(f, "finished on"))[-4:])
            for f in tablas.get("certifications", []) if _col(f, "name")
        ],
        idiomas=[Idioma(nombre=_col(f, "name"), nivel=_col(f, "proficiency"))
                 for f in tablas.get("languages", []) if _col(f, "name")],
    )
    avisos = ["linkedin-sin-logros"] if experiencia and not any(e.logros for e in experiencia) else []
    return cv, avisos
