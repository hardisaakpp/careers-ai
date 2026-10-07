"""Cuántos años de experiencia pide una oferta, estimado a partir de su título y su descripción.

Es una estimación por reglas (no un modelo): explicable y sin sorpresas. El texto de la oferta es de terceros y
solo se lee, nunca se interpreta como instrucciones. Devuelve None cuando la oferta no dice nada del nivel: en
ese caso no se descarta, porque no hay base para hacerlo.
"""

from __future__ import annotations

import re

# Un título «Senior» equivale a pedir ~5 años; liderazgo y arquitectura, ~7. Son los umbrales habituales del sector.
AÑOS_SENIOR = 5
AÑOS_LIDER = 7
MAX_CREIBLE = 15  # «20 years of experience» casi seguro habla de la empresa, no del puesto

_LIDER = re.compile(
    r"(?<!\w)(lead|principal|staff|architect|arquitect[oa]|head of|director|manager|gerente|vp)(?!\w)", re.I)
_SENIOR = re.compile(r"(?<!\w)(senior|sr\.?|sênior)(?!\w)", re.I)
_JUNIOR = re.compile(r"(?<!\w)(junior|jr\.?|entry[- ]level|intern(?:ship)?|trainee|graduate|apprentice|pasante)(?!\w)", re.I)

_NUM = r"(\d{1,2})"
_ANOS = r"(?:years?|yrs?|años?)"
_EXP = r"(?:experience|exp\b|experiencia)"
# «5+ years of (relevant|professional…) experience», «3-5 years experience», «5 años de experiencia»
_ANOS_DE_EXPERIENCIA = re.compile(
    rf"{_NUM}\s*(?:\+|plus)?\s*(?:(?:[-–]|to|a)\s*\d{{1,2}}\s*)?(?:or more\s+)?{_ANOS}"
    rf"(?:\s+(?:of|de))?(?:\s+(?:relevant|professional|hands-on|commercial|proven|solid|work|industry|software|"
    rf"development|backend|frontend|full[- ]stack|relevante|profesional)){{0,3}}\s+(?:de\s+)?{_EXP}", re.I)
# «experience: 5+ years», «experiencia de 3 años»
_EXPERIENCIA_DE = re.compile(rf"{_EXP}[^.\n]{{0,30}}?{_NUM}(?:\s*(?:[-–]|to|a)\s*\d{{1,2}})?\s*\+?\s*{_ANOS}", re.I)
# «at least 5 years», «minimum of 4 years», «mínimo 3 años»
_MINIMO = re.compile(
    rf"(?:at least|minimum(?: of)?|min\.?|mínimo(?: de)?|al menos)\s*{_NUM}(?:\s*(?:[-–]|to|a)\s*\d{{1,2}})?\s*\+?\s*{_ANOS}", re.I)


def _anos_en_texto(descripcion: str) -> int | None:
    """El mayor requisito de años que menciona la descripción (en un rango «3-5», el mínimo: 3)."""
    cifras = [
        int(m.group(1))
        for patron in (_ANOS_DE_EXPERIENCIA, _EXPERIENCIA_DE, _MINIMO)
        for m in patron.finditer(descripcion)
    ]
    validas = [n for n in cifras if 0 < n <= MAX_CREIBLE]
    return max(validas) if validas else None


def _anos_por_titulo(titulo: str) -> int | None:
    if _LIDER.search(titulo):
        return AÑOS_LIDER
    if _SENIOR.search(titulo):
        return AÑOS_SENIOR
    return 0 if _JUNIOR.search(titulo) else None


def anos_requeridos(titulo: str, descripcion: str) -> int | None:
    """Años de experiencia que la oferta pide, o None si no se puede saber. Manda el más exigente de los dos
    indicios: un puesto «Developer» que en su descripción pide «5+ years» es un puesto de 5 años."""
    indicios = [n for n in (_anos_por_titulo(titulo), _anos_en_texto(descripcion)) if n is not None]
    return max(indicios) if indicios else None
