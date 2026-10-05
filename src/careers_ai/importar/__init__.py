"""Importar una hoja de vida existente (PDF, DOCX o el ZIP de LinkedIn) como borrador para el formulario."""

from __future__ import annotations

import io
import zipfile

from ..modelo import Cv
from .errores import ImportacionError
from .extraer import Llm, extraer, ollama_importar
from .linkedin import desde_zip
from .texto import MAX_BYTES, texto_de_docx, texto_de_pdf


def importar(datos: bytes, llm: Llm = ollama_importar) -> tuple[Cv, str, list[str]]:
    """(borrador, origen, avisos). El formato se reconoce por el contenido, nunca por el nombre."""
    if len(datos) > MAX_BYTES:
        raise ImportacionError("demasiado-grande")
    if datos.startswith(b"%PDF"):
        cv, avisos = extraer(texto_de_pdf(datos), llm)
        return cv, "pdf", avisos
    if datos.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(datos)) as z:
                es_docx = "word/document.xml" in z.namelist()
        except zipfile.BadZipFile as e:
            raise ImportacionError("ilegible") from e
        if es_docx:
            cv, avisos = extraer(texto_de_docx(datos), llm)
            return cv, "docx", avisos
        cv, avisos = desde_zip(datos)
        return cv, "linkedin", avisos
    raise ImportacionError("formato-desconocido")


__all__ = ["ImportacionError", "importar"]
