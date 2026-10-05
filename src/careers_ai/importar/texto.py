"""Texto plano de un PDF o un DOCX, en orden de lectura.

Un CV de dos columnas (barra lateral + cuerpo) mezcla sus líneas si se extrae renglón a renglón, así que
se detecta el canal vertical entre columnas y se lee cada una por separado. Todo es dato no confiable:
se limita tamaño, páginas y caracteres, y nada se ejecuta.
"""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

import pdfplumber

from .errores import ImportacionError

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGINAS = 8
MAX_CARACTERES = 30_000
MIN_CARACTERES = 80  # menos que esto casi seguro es un escaneo sin capa de texto
MAX_DESCOMPRIMIDO = 20 * 1024 * 1024  # un DOCX es un ZIP: se acota lo que se descomprime
CANAL_MIN = 12.0  # ancho mínimo (pt) del hueco que separa dos columnas

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _canal(palabras: list[dict], ancho: float) -> float | None:
    """Posición x del canal que separa dos columnas, o None si la página es de una sola."""
    if len(palabras) < 20:
        return None
    ocupado = sorted((w["x0"], w["x1"]) for w in palabras)
    fin, mejor = ocupado[0][1], None
    for x0, x1 in ocupado[1:]:
        if x0 - fin >= CANAL_MIN and 0.2 * ancho < fin < 0.8 * ancho:
            if mejor is None or x0 - fin > mejor[1] - mejor[0]:
                mejor = (fin, x0)
        fin = max(fin, x1)
    return (mejor[0] + mejor[1]) / 2 if mejor else None


def _pagina(pagina) -> str:
    palabras = pagina.extract_words()
    x = _canal(palabras, float(pagina.width))
    if x is None:
        return pagina.extract_text() or ""
    x0, arriba, x1, abajo = pagina.bbox  # no siempre empieza en (0, 0)
    izquierda = pagina.crop((x0, arriba, x, abajo)).extract_text() or ""
    derecha = pagina.crop((x, arriba, x1, abajo)).extract_text() or ""
    return f"{izquierda}\n\n{derecha}"


def _limpiar(texto: str) -> str:
    texto = texto.replace("\x00", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _validar(texto: str) -> str:
    texto = _limpiar(texto)
    if len(texto) < MIN_CARACTERES:
        raise ImportacionError("sin-texto")
    return texto[:MAX_CARACTERES]


def texto_de_pdf(datos: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            paginas = [_pagina(p) for p in pdf.pages[:MAX_PAGINAS]]
    except Exception as e:  # noqa: BLE001 - pdfminer lanza de todo ante un PDF dañado
        raise ImportacionError("ilegible") from e
    return _validar("\n\n".join(paginas))


def _texto_parrafo(p: ElementTree.Element) -> str:
    return "".join(
        (t.text or "") if t.tag == f"{_W}t" else ("\n" if t.tag in (f"{_W}br", f"{_W}cr") else "\t" if t.tag == f"{_W}tab" else "")
        for t in p.iter()
    )


def texto_de_docx(datos: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            info = z.getinfo("word/document.xml")
            if info.file_size > MAX_DESCOMPRIMIDO:
                raise ImportacionError("demasiado-grande")
            raiz = ElementTree.fromstring(z.read(info))
    except ImportacionError:
        raise
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as e:
        raise ImportacionError("ilegible") from e
    # Párrafos en orden de documento; las celdas de tablas (CV con plantilla de tabla) también son párrafos.
    lineas = [_texto_parrafo(p) for p in raiz.iter(f"{_W}p")]
    return _validar("\n".join(lineas))
