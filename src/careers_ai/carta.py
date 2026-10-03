"""Carta de presentación determinista: plantilla + datos verificados, sin texto libre de un modelo.

Solo menciona tecnologías que están en el CV Y en la oferta, así no puede afirmar nada falso
ni repetir instrucciones escondidas en la oferta.
"""

from __future__ import annotations

from .modelo import Cv
from .modelos import Oferta
from .ranking.ranking import _contiene


def coincidencias(cv: Cv, oferta: Oferta) -> list[str]:
    pajar = f"{oferta.titulo} {' '.join(oferta.etiquetas)} {oferta.descripcion}"
    return [t for t in sorted(cv.tecnologias()) if _contiene(pajar, t)]


def redactar(cv: Cv, oferta: Oferta) -> str:
    """Una hoja de vida a medio llenar también produce una carta válida: cada dato que falta simplemente se omite."""
    comunes = coincidencias(cv, oferta)[:5]
    presentacion = f"Me interesa la vacante «{oferta.titulo}»."
    if cv.titular.strip():
        presentacion += f" Soy {cv.titular.strip().lower()}"
        presentacion += f" y {_minuscula(cv.resumen.strip())}" if cv.resumen.strip() else "."
    elif cv.resumen.strip():
        presentacion += f" {cv.resumen.strip()}"
    lineas = [f"Estimado equipo de {oferta.empresa or 'selección'}:", "", presentacion]
    if comunes:
        lineas += ["", f"Mi experiencia coincide con lo que buscan en: {', '.join(comunes)}."]
    ultimo = cv.experiencia[0] if cv.experiencia else None
    if ultimo and ultimo.logros and ultimo.organizacion.strip():
        lineas += ["", f"En {ultimo.organizacion}: {ultimo.logros[0]}"]
    firma = [cv.nombre, cv.contacto.email]
    lineas += ["", "Adjunto mi hoja de vida. Quedo atento a una conversación.", "", "Saludos,", *[d for d in firma if d.strip()]]
    return "\n".join(lineas) + "\n"


def _minuscula(texto: str) -> str:
    return texto[0].lower() + texto[1:]
