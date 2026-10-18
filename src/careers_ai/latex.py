"""Escape de texto para LaTeX y render de la plantilla.

Todo texto del CV (que puede venir de una oferta o de un modelo) se escapa
antes de entrar al documento: un `\\input{...}` en un logro no debe ejecutarse.
"""

from __future__ import annotations

from importlib import resources
from urllib.parse import urlparse

from jinja2 import Environment, StrictUndefined

from .enfasis import a_latex
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


# Etiquetas que solo nombran el sitio: el icono ya lo dice, así que en su lugar se muestra el usuario de la dirección.
_ETIQUETAS_GENERICAS = {"github", "gitlab", "linkedin", "twitter", "x", "web", "sitio web", "website",
                        "enlace", "link"}


def info_enlace(etiqueta: str, url: str) -> tuple[str, str]:
    """(icono, texto) de un enlace de contacto. El texto es lo que la persona escribió en la etiqueta
    («CarlosOrtiz»); solo si la dejó vacía o puso el nombre del sitio («GitHub»), que el icono ya
    dice, se muestra el usuario de la dirección (github.com/**usuario**)."""
    host, partes = _sitio(url)
    icono = next((i for h, i in _ICONOS.items() if host == h or host.endswith("." + h)), _ICONO_WEB)
    etiqueta = etiqueta.strip()
    if etiqueta and etiqueta.casefold() not in _ETIQUETAS_GENERICAS:
        return icono, etiqueta
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
    env.filters["tex"] = lambda texto: a_latex(escapar(texto))  # **texto** → negrita, ya escapado
    return env


IDIOMAS = ("es", "en")

# Rótulos fijos de la plantilla por idioma; el contenido de la persona no pasa por aquí.
ROTULOS = {
    "es": {"perfil": "Perfil profesional", "educacion": "Educación", "experiencia": "Experiencia laboral",
           "investigacion": "Investigación", "proyectos": "Proyectos", "habilidades": "Habilidades",
           "certificaciones": "Certificaciones", "idiomas": "Idiomas", "referencias": "Referencias",
           "actual": "actual", "enlace": "enlace"},
    "en": {"perfil": "Professional Summary", "educacion": "Education", "experiencia": "Work Experience",
           "investigacion": "Research", "proyectos": "Projects", "habilidades": "Skills",
           "certificaciones": "Certifications", "idiomas": "Languages", "referencias": "References",
           "actual": "Present", "enlace": "link"},
}


def renderizar(cv: Cv, plantilla: str = "clasica.tex", idioma: str = "es") -> str:
    if idioma not in ROTULOS:
        raise ValueError(f"idioma no soportado: {idioma}")
    fuente = resources.files("careers_ai").joinpath("templates", plantilla).read_text("utf-8")
    visible = cv.para_pdf()
    linea = linea_contacto(visible, iconos=ICONOS_OCULTOS not in cv.ocultas)
    return _entorno().from_string(fuente).render(cv=visible, contacto_linea=linea, L=ROTULOS[idioma])
