"""Énfasis manual: la persona marca con `**texto**` lo que quiere resaltar y en el PDF sale en negrita.

Es texto plano (no hay formato oculto): sobrevive a copiar, a guardar y a la traducción, y el PDF sigue siendo
legible para los sistemas de selección. Una marca sin pareja se descarta: nunca llega al documento.
"""

from __future__ import annotations

import re

# Dentro de una línea y sin espacios pegados a las marcas: `** a **` no resalta, `**a**` sí.
_PAR = re.compile(r"\*\*(?=\S)([^\n]+?)(?<=\S)\*\*")


def sin_enfasis(texto: str) -> str:
    """El texto sin marcas, para donde no hay negrita (cartas, vistas de texto plano)."""
    return _PAR.sub(r"\1", texto).replace("**", "")


def a_latex(escapado: str) -> str:
    """Convierte las marcas de un texto YA escapado a `\\textbf{}`. Escapar primero es lo que lo hace seguro:
    el contenido de la persona nunca llega al documento como comando."""
    return _PAR.sub(lambda m: r"\textbf{" + m.group(1) + "}", escapado).replace("**", "")
