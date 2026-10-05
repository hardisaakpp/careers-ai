"""Escape de texto para LaTeX y render de la plantilla.

Todo texto del CV (que puede venir de una oferta o de un modelo) se escapa
antes de entrar al documento: un `\\input{...}` en un logro no debe ejecutarse.
"""

from __future__ import annotations

from importlib import resources

from jinja2 import Environment, StrictUndefined

from .modelo import Cv

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escapar(texto: str) -> str:
    return "".join(_ESCAPES.get(c, c) for c in texto)


def _entorno() -> Environment:
    # Delimitadores que no chocan con la sintaxis de LaTeX.
    env = Environment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        autoescape=False,
    )
    env.filters["tex"] = escapar
    return env


def renderizar(cv: Cv, plantilla: str = "clasica.tex") -> str:
    fuente = resources.files("careers_ai").joinpath("templates", plantilla).read_text("utf-8")
    return _entorno().from_string(fuente).render(cv=cv.para_pdf())
