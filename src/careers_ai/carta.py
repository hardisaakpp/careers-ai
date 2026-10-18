"""Carta de presentación determinista: plantilla + datos verificados, sin texto libre de un modelo.

Solo menciona tecnologías que están en el CV Y en la oferta, así no puede afirmar nada falso
ni repetir instrucciones escondidas en la oferta.
"""

from __future__ import annotations

from .enfasis import sin_enfasis
from .modelo import Cv
from .modelos import Oferta
from .ranking.ranking import _contiene


def coincidencias(cv: Cv, oferta: Oferta) -> list[str]:
    pajar = f"{oferta.titulo} {' '.join(oferta.etiquetas)} {oferta.descripcion}"
    return [t for t in sorted(cv.tecnologias()) if _contiene(pajar, t)]


def redactar(cv: Cv, oferta: Oferta) -> str:
    """Una hoja de vida a medio llenar también produce una carta válida: cada dato que falta simplemente se omite."""
    comunes = coincidencias(cv, oferta)[:5]
    resumen = sin_enfasis(cv.resumen).strip()  # la carta es texto plano: sin las marcas de negrita
    presentacion = f"Me interesa la vacante «{oferta.titulo}»."
    if cv.titular.strip():
        presentacion += f" Soy {cv.titular.strip().lower()}"
        presentacion += f" y {_minuscula(resumen)}" if resumen else "."
    elif resumen:
        presentacion += f" {resumen}"
    lineas = [f"Estimado equipo de {oferta.empresa or 'selección'}:", "", presentacion]
    if comunes:
        lineas += ["", f"Mi experiencia coincide con lo que buscan en: {', '.join(comunes)}."]
    ultimo = cv.experiencia[0] if cv.experiencia else None
    if ultimo and ultimo.logros and ultimo.organizacion.strip():
        lineas += ["", f"En {ultimo.organizacion}: {sin_enfasis(ultimo.logros[0])}"]
    firma = [cv.nombre, cv.contacto.email]
    lineas += ["", "Adjunto mi hoja de vida. Quedo atento a una conversación.", "", "Saludos,", *[d for d in firma if d.strip()]]
    return "\n".join(lineas) + "\n"


def _minuscula(texto: str) -> str:
    """Pasa la primera letra a minúscula para encadenar la frase, salvo en siglas y nombres propios (APIs, SQL, Docker)."""
    palabra = texto.split(maxsplit=1)[0]
    if palabra.isupper() or palabra[1:] != palabra[1:].lower() or palabra[0].isupper() and palabra not in _COMUNES:
        return texto
    return texto[0].lower() + texto[1:]


_COMUNES = {"Desarrollo", "Desarrollador", "Desarrolladora", "Ingeniero", "Ingeniera", "Soy", "Experiencia", "Trabajo", "Construyo", "Hago"}
