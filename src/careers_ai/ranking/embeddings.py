"""Embeddings con Ollama (bge-m3). Cambiar de proveedor = reemplazar este módulo."""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

Embedder = Callable[[Sequence[str]], list[list[float]]]
MODELO = os.environ.get("CARRERA_MODELO_EMBEDDINGS", "bge-m3")
OLLAMA = os.environ.get("CARRERA_OLLAMA_URL", "http://localhost:11434")


def _pedir(textos: Sequence[str], cpu: bool) -> list[list[float]]:
    cuerpo = json.dumps({"model": MODELO, "input": list(textos), "keep_alive": "10m",
                         "options": {"num_gpu": 0} if cpu else {}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/embed", cuerpo, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310
        return json.loads(r.read())["embeddings"]


def ollama(textos: Sequence[str]) -> list[list[float]]:
    """GPU primero (rápido). Con bge-m3 algunos textos cortos dan NaN en fp16 y Ollama responde 500:
    ese lote se repite en CPU, que es más lento pero exacto."""
    vectores: list[list[float]] = []
    for i in range(0, len(textos), 8):
        lote = textos[i:i + 8]
        try:
            vectores.extend(_pedir(lote, cpu=False))
        except urllib.error.HTTPError:
            vectores.extend(_pedir(lote, cpu=True))
    return vectores


def coseno(a: Sequence[float], b: Sequence[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return 0.0 if na == 0 or nb == 0 else sum(x * y for x, y in zip(a, b)) / (na * nb)


class ConCache:
    """Evita re-embeber textos iguales entre corridas (clave = hash del texto + modelo)."""

    def __init__(self, base: Embedder, db) -> None:
        self.base, self.db = base, db
        db.execute("CREATE TABLE IF NOT EXISTS vectores (h TEXT PRIMARY KEY, v TEXT NOT NULL)")

    @staticmethod
    def _clave(texto: str) -> str:
        return hashlib.sha256(f"{MODELO}\n{texto}".encode()).hexdigest()

    def tiene(self, texto: str) -> bool:
        return self.db.execute("SELECT 1 FROM vectores WHERE h=?", (self._clave(texto),)).fetchone() is not None

    def __call__(self, textos: Sequence[str]) -> list[list[float]]:
        claves = [self._clave(t) for t in textos]
        hallados = {h: json.loads(v) for h, v in self.db.execute(
            f"SELECT h,v FROM vectores WHERE h IN ({','.join('?' * len(claves))})", claves)} if claves else {}
        faltan = [(h, t) for h, t in zip(claves, textos) if h not in hallados]
        # Por tandas y guardando cada una: si la corrida se interrumpe, lo ya calculado no se pierde.
        for i in range(0, len(faltan), 16):
            tanda = faltan[i:i + 16]
            for (h, _), v in zip(tanda, self.base([t for _, t in tanda])):
                hallados[h] = v
                self.db.execute("INSERT OR REPLACE INTO vectores VALUES (?,?)", (h, json.dumps(v)))
            self.db.commit()
        return [hallados[h] for h in claves]
