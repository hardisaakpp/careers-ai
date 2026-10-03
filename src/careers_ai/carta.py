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
    comunes = coincidencias(cv, oferta)[:5]
    lineas = [
        f"Estimado equipo de {oferta.empresa or 'selección'}:",
        "",
        f"Me interesa la vacante «{oferta.titulo}». Soy {cv.titular.lower()} y {cv.resumen[0].lower()}{cv.resumen[1:]}",
    ]
    if comunes:
        lineas += ["", f"Mi experiencia coincide con lo que buscan en: {', '.join(comunes)}."]
    ultimo = cv.experiencia[0] if cv.experiencia else None
    if ultimo and ultimo.logros:
        lineas += ["", f"En {ultimo.organizacion}: {ultimo.logros[0]}"]
    lineas += ["", "Adjunto mi hoja de vida. Quedo atento a una conversación.", "", "Saludos,", cv.nombre,
               cv.contacto.email]
    return "\n".join(lineas) + "\n"
