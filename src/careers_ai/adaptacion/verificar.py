"""Compuerta dura: un CV adaptado solo puede ser un subconjunto reordenado del original.

No confía en el modelo: compara contra el YAML. Si algo no está en el original, falla.
"""

from __future__ import annotations

from ..modelo import Cv


def _minus(valores) -> set[str]:
    return {v.casefold() for v in valores}


def problemas(original: Cv, adaptado: Cv) -> list[str]:
    """Lista vacía = el adaptado es fiel. Cualquier elemento es un motivo para rechazarlo."""
    out: list[str] = []
    for campo in ("nombre", "titular", "resumen", "contacto"):
        if getattr(original, campo) != getattr(adaptado, campo):
            out.append(f"{campo} modificado")

    base_exp = {(e.cargo, e.organizacion, e.desde, e.hasta): e for e in original.experiencia}
    for e in adaptado.experiencia:
        o = base_exp.get((e.cargo, e.organizacion, e.desde, e.hasta))
        if o is None:
            out.append(f"experiencia inventada o alterada: {e.cargo} @ {e.organizacion}")
            continue
        if not set(e.logros) <= set(o.logros):
            out.append(f"logro no presente en el original ({e.cargo})")
        if not _minus(e.tecnologias) <= _minus(o.tecnologias):
            out.append(f"tecnología añadida en {e.cargo}")

    base_proy = {p.nombre: p for p in original.proyectos}
    for p in adaptado.proyectos:
        o = base_proy.get(p.nombre)
        if o is None or (p.descripcion, p.url) != (o.descripcion, o.url):
            out.append(f"proyecto inventado o alterado: {p.nombre}")
        elif not _minus(p.tecnologias) <= _minus(o.tecnologias):
            out.append(f"tecnología añadida en proyecto {p.nombre}")

    if adaptado.educacion != original.educacion:
        out.append("educación modificada")

    if not _minus(i for g in adaptado.habilidades for i in g.items) <= _minus(original.tecnologias()):
        out.append("habilidad que no está en el original")
    return out
