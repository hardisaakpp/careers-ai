"""Escape de texto para LaTeX y render de la plantilla.

Todo texto del CV (que puede venir de una oferta o de un modelo) se escapa
antes de entrar al documento: un `\\input{...}` en un logro no debe ejecutarse.
"""

from __future__ import annotations

from importlib import resources
from urllib.parse import urlparse

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


# Iconos de FontAwesome por sitio. Son comandos fijos de aquí (nunca texto de la persona), así que no se escapan.
_ICONOS = {"github.com": r"\faGithub", "gitlab.com": r"\faGitlab", "linkedin.com": r"\faLinkedin",
           "twitter.com": r"\faTwitter", "x.com": r"\faTwitter"}
_ICONO_WEB = r"\faGlobe"
ICONOS_OCULTOS = "contacto.iconos"  # clave de `ocultas`: encabezado sin iconos


# La barra va pegada al elemento que sigue (\nobreak): si la línea se parte, no queda una barra suelta al final.
SEPARADOR = r"\ \textbar\nobreak\ "


def _sitio(url: str) -> tuple[str, list[str]]:
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower().removeprefix("www.")
    except ValueError:  # p. ej. «http://[» : no es una dirección, no hay sitio que reconocer
        return "", []
    return host, [x for x in p.path.split("/") if x]


def info_enlace(etiqueta: str, url: str) -> tuple[str, str]:
    """(icono, texto) de un enlace de contacto. En GitHub y LinkedIn se muestra el usuario («hardisaakpp»),
    no «GitHub»: el icono ya dice de qué sitio es. En cualquier otro, la etiqueta que puso la persona."""
    host, partes = _sitio(url)
    icono = next((i for h, i in _ICONOS.items() if host == h or host.endswith("." + h)), _ICONO_WEB)
    usuario = ""
    if host.endswith(("github.com", "gitlab.com")):
        usuario = partes[0] if partes else ""
    elif host.endswith("linkedin.com"):
        usuario = partes[1] if len(partes) > 1 and partes[0] in ("in", "pub", "company") else ""
    return icono, usuario or etiqueta or host


def linea_contacto(cv: Cv, iconos: bool) -> str:
    """La línea del encabezado, ya en LaTeX y con todo el texto de la persona escapado."""
    c = cv.contacto
    partes: list[str] = []
    if c.telefono:
        partes.append((r"\faPhone\ " if iconos else "") + escapar(c.telefono))
    if c.email:
        partes.append((r"\faEnvelope\ " if iconos else "") + escapar(c.email))
    for etiqueta, url in c.enlaces.items():
        icono, texto = info_enlace(etiqueta, url)
        prefijo = icono + r"\ " if iconos else ""
        partes.append(r"\href{" + escapar(url) + "}{" + prefijo + escapar(texto if iconos else etiqueta) + "}")
    if c.ubicacion:
        partes.append(escapar(c.ubicacion))
    return SEPARADOR.join(partes)


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
    visible = cv.para_pdf()
    linea = linea_contacto(visible, iconos=ICONOS_OCULTOS not in cv.ocultas)
    return _entorno().from_string(fuente).render(cv=visible, contacto_linea=linea)
