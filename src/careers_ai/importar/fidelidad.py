"""Compuerta de fidelidad: lo que el modelo extrae solo vale si está en el documento.

El modelo ordena y clasifica, no redacta. Cada texto que devuelve se busca (sin mayúsculas, tildes,
espacios ni signos, para tolerar saltos de línea y guiones de corte) en el texto original; lo que no
aparece se descarta. Es la misma regla de `adaptacion/verificar.py`: un CV importado no puede traer
nada que la persona no haya escrito.
"""

from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.casefold())
    return re.sub(r"[^0-9a-z]", "", "".join(c for c in sin_tildes if not unicodedata.combining(c)))


class Fuente:
    """El documento original, normalizado una vez, y la cuenta de lo que no se pudo verificar."""

    def __init__(self, texto: str) -> None:
        self._norm = normalizar(texto)
        self.descartados = 0

    def esta(self, valor: str) -> bool:
        n = normalizar(valor)
        return not n or n in self._norm

    def texto(self, valor: str) -> str:
        """El valor tal cual si está en el documento; si no, vacío (y se cuenta)."""
        if self.esta(valor):
            return valor.strip()
        self.descartados += 1
        return ""

    def lista(self, valores: list[str]) -> list[str]:
        return [v.strip() for v in valores if v.strip() and self._conserva(v)]

    def _conserva(self, valor: str) -> bool:
        if self.esta(valor):
            return True
        self.descartados += 1
        return False
