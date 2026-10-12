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
# «Semi Senior», «SSR», «Mid-level»: nivel intermedio, ~3 años. «Mid-Senior» es de LinkedIn y ya pide ~4.
_INTERMEDIO = re.compile(
    r"(?<!\w)(semi[- ]?senior|semi[- ]?sr\.?|ssr\.?|mid[- ]?level|intermedi[oa]|intermediate|experienced)(?!\w)", re.I)
_MID_SENIOR = re.compile(r"(?<!\w)mid[- ]?senior(?!\w)", re.I)
# Los escalones numerados: «Engineer II» (~3 años) y «III»/«IV» (~5). Distingue mayúsculas: «ii» no es un nivel.
_NIVEL_II = re.compile(r"(?<![\w.])II(?![\w.])")
_NIVEL_III = re.compile(r"(?<![\w.])(?:III|IV)(?![\w.])")
AÑOS_INTERMEDIO = 3
AÑOS_MID_SENIOR = 4
# Lo que la descripción dice del perfil buscado: «Buscamos un Full Stack Semi Senior», «looking for a senior engineer»,
# «Backend Developer Senior». Se exige la frase de búsqueda o el cargo pegado a «senior»: un «5 Senior Developers» en la
# presentación del equipo no es un requisito. «Junior and Senior» no dice nada a favor de uno u otro.
# Hasta 3 palabras de cargo entre la frase y «senior»; una preposición corta el vínculo («embedded with senior sales leaders»).
_PALABRA_NIVEL = r"(?:(?!(?:with|of|to|for|and|the|in|on|y|con|de|para|junto)\b)[\w/.+#&-]+\s+){0,3}?"
_SENIOR_PURO = r"(?<!semi-)(?<!semi )(?<!semi)(?<!mid-)(?<!mid )(?:senior|sr\.?)(?!\w)"  # «semi senior» no es «senior»
_BUSCA = r"(?:looking for|seeking|searching for|we(?:'re| are)? hiring|we need|buscamos|buscando|requerimos|necesitamos)"
_ART = r"(?:an?\s+|un[a]?\s+)?"
_PERFIL_SENIOR = re.compile(
    rf"{_BUSCA}\s+{_ART}{_PALABRA_NIVEL}{_SENIOR_PURO}"
    rf"|(?<!\w)senior[- ]level(?!\w)"
    rf"|(?:developer|engineer|desarrollador[a]?|ingenier[oa]|programador[a]?)\s+{_SENIOR_PURO}"
    rf"|(?:ser|como|be|as)\s+{_ART}{_PALABRA_NIVEL}{_SENIOR_PURO}", re.I)
_PERFIL_INTERMEDIO = re.compile(
    rf"{_BUSCA}\s+(?:an?\s+|un[a]?\s+)?{_PALABRA_NIVEL}(?:semi[- ]?senior|ssr|mid[- ]?level)(?!\w)", re.I)
# «Semi Senior» casi no tiene otro uso en una descripción que nombrar el nivel del puesto.
_INTERMEDIO_EXPLICITO = re.compile(r"(?<!\w)(?:semi[- ]?senior|ssr)(?!\w)", re.I)
_JUNIOR = re.compile(r"(?<!\w)(junior|jr\.?|entry[- ]level|intern(?:ship)?|trainee|graduate|apprentice|pasante)(?!\w)", re.I)

_NUM = r"(?<![\d,.])(\d{1,2})"
_ANOS = r"(?:years?|yrs?|años?)"
_EXP = r"(?:experience|exp\b|experiencia)"
# «5+ years of (relevant|professional…) experience», «3-5 years experience», «5 años de experiencia»
_ANOS_DE_EXPERIENCIA = re.compile(
    rf"{_NUM}\s*(?:\+|plus)?\s*(?:(?:[-–]|to|a)\s*\d{{1,2}}\s*)?(?:or more\s+)?{_ANOS}"
    rf"(?:\s+(?:of|de))?(?:\s+(?:relevant|professional|hands-on|commercial|proven|solid|work|industry|software|"
    rf"development|engineering|testing|coding|programming|web|technical|related|practical|prior|backend|frontend|full[- ]stack|relevante|profesional)){{0,3}}\s+(?:de\s+)?{_EXP}", re.I)
# «4+ años en C#», «5 o más años», «5–10 years», «de 3 a 5 años en desarrollo»: la cifra sola no basta («4 years» puede ser
# la edad del producto), así que se exige una palabra de oficio cerca. El «+», «o más» o un rango marcan un requisito.
_MAS_O_RANGO = re.compile(
    rf"{_NUM}\s*(?:(?:\+|plus|or more|o más|o mas|y más)|(?:[-–—]|to|a)\s*\d{{1,2}}\s*\+?)\s*{_ANOS}\b"
    r"(?!\s*(?:de\s+)?(?:estudios?|carrera|duraci|edad|old\b))", re.I)
_OFICIO = re.compile(
    r"experien|trayectoria|professional|profesional|development|desarroll|engineer|ingenier|software|programa|coding|"
    r"working|trabaj|building|hands-on|backend|back-end|frontend|front-end|full[- ]?stack|testing|background", re.I)
_VENTANA = (60, 90)
# «experience: 5+ years», «experiencia de 3 años»
_EXPERIENCIA_DE = re.compile(rf"{_EXP}[^.\n]{{0,30}}?{_NUM}(?:\s*(?:[-–]|to|a)\s*\d{{1,2}})?\s*\+?\s*{_ANOS}", re.I)
# «at least 5 years», «minimum of 4 years», «mínimo 3 años»
_MINIMO = re.compile(
    rf"(?:at least|minimum(?: of)?|min\.?|mínimo(?: de)?|al menos)\s*{_NUM}(?:\s*(?:[-–]|to|a)\s*\d{{1,2}})?\s*\+?\s*{_ANOS}", re.I)


def _con_oficio_cerca(texto: str, m: re.Match[str]) -> bool:
    antes, despues = _VENTANA
    return _OFICIO.search(texto, max(0, m.start() - antes), m.end() + despues) is not None


def _anos_en_texto(descripcion: str) -> int | None:
    """El mayor requisito de años que menciona la descripción (en un rango «3-5», el mínimo: 3)."""
    cifras = [
        int(m.group(1))
        for patron in (_ANOS_DE_EXPERIENCIA, _EXPERIENCIA_DE, _MINIMO)
        for m in patron.finditer(descripcion)
    ]
    cifras += [int(m.group(1)) for m in _MAS_O_RANGO.finditer(descripcion) if _con_oficio_cerca(descripcion, m)]
    validas = [n for n in cifras if 0 < n <= MAX_CREIBLE]
    return max(validas) if validas else None


def _anos_por_titulo(titulo: str) -> int | None:
    if _LIDER.search(titulo):
        return AÑOS_LIDER
    if _MID_SENIOR.search(titulo):
        return AÑOS_MID_SENIOR
    if _INTERMEDIO.search(titulo):  # antes que «senior»: «semi senior» lo contiene
        return AÑOS_INTERMEDIO
    if _SENIOR.search(titulo) or _NIVEL_III.search(titulo):
        return AÑOS_SENIOR
    if _NIVEL_II.search(titulo):
        return AÑOS_INTERMEDIO
    return 0 if _JUNIOR.search(titulo) else None


def _nivel_en_texto(descripcion: str) -> int | None:
    """El nivel que la descripción dice buscar, en años equivalentes; None si no lo dice."""
    niveles = []
    if _PERFIL_INTERMEDIO.search(descripcion) or _INTERMEDIO_EXPLICITO.search(descripcion):
        niveles.append(AÑOS_INTERMEDIO)
    senior = _PERFIL_SENIOR.search(descripcion)
    if senior and not _JUNIOR.search(senior.group(0)):
        niveles.append(AÑOS_SENIOR)
    return max(niveles) if niveles else None


def anos_requeridos(titulo: str, descripcion: str) -> int | None:
    """Años de experiencia que la oferta pide, o None si no se puede saber. Manda el más exigente de los dos
    indicios: un puesto «Developer» que en su descripción pide «5+ years» es un puesto de 5 años."""
    indicios = [n for n in (_anos_por_titulo(titulo), _anos_en_texto(descripcion), _nivel_en_texto(descripcion)) if n is not None]
    return max(indicios) if indicios else None
