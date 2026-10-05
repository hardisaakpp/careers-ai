"""Fallas de importación con un código estable: api-careers y la interfaz las traducen, nunca muestran el detalle técnico."""

from __future__ import annotations


class ImportacionError(Exception):
    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo


# Códigos: formato-desconocido, demasiado-grande, sin-texto (p. ej. PDF escaneado), ilegible, zip-sin-datos
