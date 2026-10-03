import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from careers_ai.api import Ajustes, crear_app

CLAVE = "clave-de-pruebas-0123456789"
CV = yaml.safe_load((Path(__file__).parent.parent / "data" / "ejemplo.yaml").read_text("utf-8"))
HEAD = {"X-Api-Key": CLAVE}


def embedder(textos):
    claves = ["backend", "api", "sales", "net"]
    return [[float(k in t.lower()) for k in claves] for t in textos]


def compilador(tex: Path) -> Path:
    pdf = tex.with_suffix(".pdf")
    pdf.write_bytes(b"%PDF-falso")
    return pdf


@pytest.fixture
def cliente(tmp_path):
    ajustes = Ajustes(CLAVE, tmp_path / "e.db", embedder=embedder,
                      llm=lambda p, e: {"logros": [[0]], "proyectos": [0], "habilidades": [".NET"]},
                      compilador=compilador)
    return TestClient(crear_app(ajustes))


def oferta(id, titulo, desc=""):
    return {"id": id, "titulo": titulo, "empresa": "Acme", "descripcion": desc}


def rank(c, ofertas, prefs=None):
    cuerpo = {"cv": CV, "ofertas": ofertas, **({"preferencias": prefs} if prefs else {})}
    return c.post("/v1/rank", json=cuerpo, headers=HEAD).json()


def rank_completo(c, ofertas, prefs=None):
    for _ in range(50):
        r = rank(c, ofertas, prefs)
        if r["pendientes"] == 0:
            return r
        time.sleep(0.1)
    raise AssertionError("no terminó el cálculo en segundo plano")


def test_exige_la_clave(cliente):
    for cabeceras in ({}, {"X-Api-Key": "otra"}):
        assert cliente.post("/v1/render", json={"cv": CV}, headers=cabeceras).status_code == 401
    assert cliente.get("/health").status_code == 200


def test_la_clave_debe_ser_larga():
    with pytest.raises(ValueError):
        Ajustes("corta", Path("x/e.db"))


def test_rank_ordena_y_explica(cliente):
    ofertas = [oferta("a", "Marketing lead", "campañas"),
               oferta("b", "Backend API engineer", "APIs con .NET y SQL Server")]
    r = rank_completo(cliente, ofertas)
    ids = [x["id"] for x in r["resultados"]]
    assert ids[0] == "b" and ".NET" in r["resultados"][0]["coinciden"]


def test_rank_aplica_reglas_duras(cliente):
    ofertas = [oferta("a", "Sales rep"), oferta("b", "Backend API engineer")]
    r = rank_completo(cliente, ofertas, {"excluir_titulos": ["sales"]})
    por_id = {x["id"]: x for x in r["resultados"]}
    assert por_id["a"]["excluida"] == "título excluido" and por_id["b"]["excluida"] is None


def test_rank_primera_vez_informa_pendientes(cliente):
    primera = rank(cliente, [oferta("a", "Backend API engineer")])
    assert primera["pendientes"] in (0, 1)
    assert rank_completo(cliente, [oferta("a", "Backend API engineer")])["pendientes"] == 0


def test_adapt_nunca_devuelve_algo_que_no_este_en_el_cv(cliente):
    r = cliente.post("/v1/adapt", json={"cv": CV, "oferta": oferta("a", "Backend")}, headers=HEAD).json()
    assert r["cv"]["nombre"] == CV["nombre"]
    assert {i for g in r["cv"]["habilidades"] for i in g["items"]} <= {".NET", "Docker", "SQL Server",
        "Next.js", "TypeScript", "C#", "Python", "SQL"}


def test_carta_menciona_solo_tecnologias_comunes(cliente):
    r = cliente.post("/v1/letter", json={"cv": CV, "oferta": oferta("a", "Dev", "Usamos .NET y Rust")},
                     headers=HEAD).json()
    assert ".NET" in r["carta"] and "Rust" not in r["carta"]


def test_render_devuelve_pdf(cliente):
    r = cliente.post("/v1/render", json={"cv": CV}, headers=HEAD)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"


def test_rechaza_cuerpos_invalidos(cliente):
    assert cliente.post("/v1/rank", json={"cv": CV, "ofertas": [{"id": "a"}]}, headers=HEAD).status_code == 422
    demasiadas = [oferta(str(i), "t") for i in range(501)]
    assert cliente.post("/v1/rank", json={"cv": CV, "ofertas": demasiadas}, headers=HEAD).status_code == 422
    assert cliente.post("/v1/render", json={"cv": {**CV, "salario": 1}}, headers=HEAD).status_code == 422


def test_carta_con_una_hoja_de_vida_incompleta_no_falla(cliente):
    """La API de negocio solo exige el nombre: titular, resumen, correo y experiencia pueden estar vacíos."""
    vacio = {"nombre": "Ana", "titular": "", "resumen": "", "contacto": {"email": "", "enlaces": {}},
             "experiencia": [], "proyectos": [], "educacion": [], "habilidades": []}
    for variante in (vacio, {**vacio, "titular": "Ingeniera"}, {**vacio, "resumen": "Hago APIs."},
                     {**vacio, "titular": "Ingeniera", "resumen": "hago APIs."}):
        r = cliente.post("/v1/letter", json={"cv": variante, "oferta": oferta("a", "Backend")}, headers=HEAD)
        assert r.status_code == 200, variante
        assert r.json()["carta"].rstrip().endswith("Ana")


def test_adapt_y_rank_con_una_hoja_de_vida_incompleta_no_fallan(cliente):
    vacio = {"nombre": "Ana", "titular": "", "resumen": "", "contacto": {"email": "", "enlaces": {}},
             "experiencia": [], "proyectos": [], "educacion": [], "habilidades": []}
    assert cliente.post("/v1/adapt", json={"cv": vacio, "oferta": oferta("a", "Backend")}, headers=HEAD).status_code == 200
    assert cliente.post("/v1/rank", json={"cv": vacio, "ofertas": [oferta("a", "Backend")]}, headers=HEAD).status_code == 200
    assert cliente.post("/v1/render", json={"cv": vacio}, headers=HEAD).status_code == 200


@pytest.mark.parametrize("resumen,esperado", [
    ("APIs in .NET con SQL Server.", "y APIs in .NET con SQL Server."),
    ("Desarrollo de APIs en .NET.", "y desarrollo de APIs en .NET."),
    ("SQL Server y Docker.", "y SQL Server y Docker."),
    ("Docker en producción.", "y Docker en producción."),
    ("hago APIs.", "y hago APIs."),
])
def test_la_carta_no_rompe_siglas_ni_nombres_propios_al_encadenar_el_resumen(cliente, resumen, esperado):
    cv = {"nombre": "Ana", "titular": "Ingeniera", "resumen": resumen, "contacto": {"email": "", "enlaces": {}},
          "experiencia": [], "proyectos": [], "educacion": [], "habilidades": []}
    carta = cliente.post("/v1/letter", json={"cv": cv, "oferta": oferta("a", "Backend")}, headers=HEAD).json()["carta"]
    assert esperado in carta
