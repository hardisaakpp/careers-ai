"""Ranking explicable: reglas duras -> afinidad semántica + tecnologías en común.

La explicación sale de datos (qué tecnologías coinciden, qué regla descartó),
no del texto de un modelo, así una oferta no puede "argumentar" su propio puntaje.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..modelo import Cv
from ..modelos import Oferta
from .embeddings import Embedder, coseno
from .preferencias import Preferencias

PESO_SEMANTICO = 0.6
PESO_TECNOLOGIAS = 0.4
COSENO_BAJO, COSENO_ALTO = 0.35, 0.70  # bge-m3: por debajo es ruido, por encima es muy afín


@dataclass
class Resultado:
    oferta: Oferta
    puntaje: float = 0.0
    excluida: str | None = None
    coinciden: list[str] = field(default_factory=list)
    faltan: list[str] = field(default_factory=list)
    similitud: float = 0.0


def _contiene(texto: str, termino: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(termino.lower())}(?![\w])", texto.lower()) is not None


def texto_oferta(o: Oferta) -> str:
    return f"{o.titulo}. {', '.join(o.etiquetas)}. {o.descripcion[:1500]}"


def texto_cv(cv: Cv) -> str:
    logros = [l for e in cv.experiencia for l in e.logros]
    return " ".join([cv.titular, cv.resumen, *logros, ", ".join(sorted(cv.tecnologias()))])


def regla_dura(o: Oferta, pref: Preferencias) -> str | None:
    if any(_contiene(o.titulo, t) for t in pref.excluir_titulos):
        return "título excluido"
    cuerpo = f"{o.titulo} {o.descripcion}"
    if any(_contiene(cuerpo, t) for t in pref.excluir_texto):
        return "texto excluido"
    if pref.ubicaciones and not any(_contiene(o.ubicacion or "worldwide", u) for u in pref.ubicaciones):
        return "ubicación no aceptada"
    pajar = f"{o.titulo} {' '.join(o.etiquetas)} {o.descripcion}"
    faltan = [t for t in pref.obligatorias if not _contiene(pajar, t)]
    if faltan:
        return f"falta tecnología obligatoria: {faltan[0]}"
    return None


def ordenar(cv: Cv, ofertas: list[Oferta], pref: Preferencias, embedder: Embedder) -> list[Resultado]:
    resultados = [Resultado(o, excluida=regla_dura(o, pref)) for o in ofertas]
    vivas = [r for r in resultados if r.excluida is None]
    if vivas:
        vectores = embedder([texto_cv(cv), *[texto_oferta(r.oferta) for r in vivas]])
        vcv, voferta = vectores[0], vectores[1:]
        tecnologias = sorted(cv.tecnologias())
        for r, v in zip(vivas, voferta):
            pajar = f"{r.oferta.titulo} {' '.join(r.oferta.etiquetas)} {r.oferta.descripcion}"
            r.coinciden = [t for t in tecnologias if _contiene(pajar, t)]
            r.similitud = coseno(vcv, v)
            sem = min(1.0, max(0.0, (r.similitud - COSENO_BAJO) / (COSENO_ALTO - COSENO_BAJO)))
            # Con pocas coincidencias ya hay señal: 4 tecnologías en común saturan el componente.
            tec = min(1.0, len(r.coinciden) / 4)
            r.puntaje = round(100 * (PESO_SEMANTICO * sem + PESO_TECNOLOGIAS * tec), 1)
    return sorted(resultados, key=lambda r: (r.excluida is not None, -r.puntaje))
