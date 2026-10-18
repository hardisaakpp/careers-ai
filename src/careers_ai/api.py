"""API interna del servicio de IA. Sin estado de negocio: recibe todo lo que necesita y devuelve un resultado.

Quien la llama (api-careers) guarda los datos. Aquí solo hay un caché de vectores, que se puede borrar.
Protegida con una clave compartida; escucha solo en la red local.
"""

from __future__ import annotations

import hmac
import os
import tempfile
import threading
from pathlib import Path
from typing import Callable, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from .adaptacion.adaptar import Llm, adaptar, ollama_json
from .carta import redactar
from .compilar import compilar
from .importar import ImportacionError, importar
from .importar.extraer import ollama_importar
from .importar.texto import MAX_BYTES
from .latex import renderizar
from .modelo import Cv
from .modelos import Oferta
from .ranking.embeddings import ConCache, Embedder, ollama
from .ranking.preferencias import Preferencias
from .ranking.ranking import ordenar, texto_oferta
from .traducir import Llm as LlmTraducir
from .traducir import TraduccionError, ollama_traducir, traducir

MAX_OFERTAS = 500


class RankIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cv: Cv
    preferencias: Preferencias = Field(default_factory=Preferencias)
    ofertas: list[Oferta] = Field(max_length=MAX_OFERTAS)


class OfertaCv(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cv: Cv
    oferta: Oferta


class RenderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cv: Cv
    idioma: Literal["es", "en"] = "es"  # rótulos de las secciones y «actual»/«Present»


class TraducirIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cv: Cv


class Ajustes:
    def __init__(self, clave: str, cache: Path, embedder: Embedder = ollama, llm: Llm = ollama_json,
                 compilador: Callable[[Path], Path] = compilar, llm_importar: Llm = ollama_importar,
                 llm_traducir: LlmTraducir = ollama_traducir) -> None:
        if len(clave) < 16:
            raise ValueError("CAREERS_AI_KEY debe tener al menos 16 caracteres")
        self.clave, self.cache, self.embedder, self.llm, self.compilador = clave, cache, embedder, llm, compilador
        self.llm_importar, self.llm_traducir = llm_importar, llm_traducir
        cache.parent.mkdir(parents=True, exist_ok=True)


def desde_entorno() -> Ajustes:
    return Ajustes(os.environ.get("CAREERS_AI_KEY", ""), Path(os.environ.get("CAREERS_AI_CACHE", "cache/embeddings.db")))


def crear_app(ajustes: Ajustes | None = None) -> FastAPI:
    a = ajustes or desde_entorno()
    app = FastAPI(title="careers-ai", docs_url=None, redoc_url=None)

    def autorizar(x_api_key: str = Header(default="")) -> None:
        if not hmac.compare_digest(x_api_key.encode(), a.clave.encode()):
            raise HTTPException(401, "clave inválida")

    def cache():
        import sqlite3
        return ConCache(a.embedder, sqlite3.connect(a.cache, check_same_thread=False))

    calculando: set[str] = set()
    cerrojo = threading.Lock()

    def precalcular(textos: list[str]) -> None:
        """La primera vez son minutos: se calcula aparte y quien llama vuelve a preguntar."""
        try:
            cache()(textos)
        finally:
            with cerrojo:
                calculando.difference_update(textos)

    @app.get("/health")
    def salud():
        return {"ok": True}

    @app.post("/v1/rank", dependencies=[Depends(autorizar)])
    async def rank(cuerpo: RankIn):
        c = cache()
        listas = [o for o in cuerpo.ofertas if c.tiene(texto_oferta(o))]
        faltan = [texto_oferta(o) for o in cuerpo.ofertas if not c.tiene(texto_oferta(o))]
        with cerrojo:
            nuevos = [t for t in faltan if t not in calculando]
            calculando.update(nuevos)
        if nuevos:
            threading.Thread(target=precalcular, args=(nuevos,), daemon=True).start()
        resultados = await run_in_threadpool(ordenar, cuerpo.cv, listas, cuerpo.preferencias, c)
        return {
            "pendientes": len(faltan),
            "resultados": [{"id": r.oferta.id, "puntaje": r.puntaje, "excluida": r.excluida,
                            "coinciden": r.coinciden, "anos": r.anos} for r in resultados],
        }

    @app.post("/v1/adapt", dependencies=[Depends(autorizar)])
    async def adaptar_cv(cuerpo: OfertaCv):
        adaptado = await run_in_threadpool(adaptar, cuerpo.cv, cuerpo.oferta, a.llm)
        return {"cv": adaptado.model_dump(mode="json"), "cambiado": adaptado != cuerpo.cv}

    @app.post("/v1/letter", dependencies=[Depends(autorizar)])
    def carta(cuerpo: OfertaCv):
        return {"carta": redactar(cuerpo.cv, cuerpo.oferta)}

    @app.post("/v1/render", dependencies=[Depends(autorizar)])
    async def render(cuerpo: RenderIn):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "cv.tex"
            tex.write_text(renderizar(cuerpo.cv, idioma=cuerpo.idioma), "utf-8")
            try:
                pdf = await run_in_threadpool(a.compilador, tex)
            except Exception as e:  # noqa: BLE001 - latexmk/docker
                raise HTTPException(422, "no se pudo compilar el CV") from e
            return Response(pdf.read_bytes(), media_type="application/pdf")

    @app.post("/v1/translate", dependencies=[Depends(autorizar)])
    async def traducir_cv(cuerpo: TraducirIn):
        """Borrador en inglés del CV (español). Nada se guarda: la persona lo revisa y lo edita."""
        try:
            en, avisos = await run_in_threadpool(traducir, cuerpo.cv, a.llm_traducir)
        except TraduccionError as e:
            raise HTTPException(502, "ia-fallo") from e
        return {"cv": en.model_dump(mode="json"), "avisos": avisos}

    @app.post("/v1/import", dependencies=[Depends(autorizar)])
    async def importar_cv(request: Request):
        """El archivo viaja crudo en el cuerpo (PDF, DOCX o ZIP de LinkedIn); el formato se reconoce por su contenido."""
        declarado = request.headers.get("content-length")
        if declarado and declarado.isdigit() and int(declarado) > MAX_BYTES:
            raise HTTPException(413, "demasiado-grande")
        datos = await request.body()
        try:
            cv, origen, avisos = await run_in_threadpool(importar, datos, a.llm_importar)
        except ImportacionError as e:
            raise HTTPException(413 if e.codigo == "demasiado-grande" else 422, e.codigo) from e
        return {"cv": cv.model_dump(mode="json"), "origen": origen, "avisos": avisos}

    return app
