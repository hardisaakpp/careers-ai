from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from careers_ai.api import Ajustes, crear_app
from careers_ai.modelo import Cv
from careers_ai.traducir import TraduccionError, fecha_en, traducir

EJEMPLO = Path(__file__).parent.parent / "data" / "ejemplo.yaml"
CLAVE = "clave-de-pruebas-0123456789"


def _cv(**cambios) -> Cv:
    datos = yaml.safe_load(EJEMPLO.read_text("utf-8"))
    datos.update(cambios)
    return Cv.model_validate(datos)


def _prompt_textos(prompt: str) -> list[str]:
    import json
    return json.loads(prompt.split("TEXTS:\n", 1)[1])


def llm_marca(prompt, esquema):
    return {"traducciones": [f"EN:{t}" for t in _prompt_textos(prompt)]}


def test_los_meses_se_traducen_sin_modelo():
    assert fecha_en("Septiembre 2025") == "September 2025"
    assert fecha_en("marzo 2025") == "March 2025"
    assert fecha_en("2022-03") == "2022-03" and fecha_en(None) is None


def test_traduce_el_texto_y_conserva_lo_demas():
    cv = _cv(resumen="Hola mundo", ocultas=["referencias"])
    en, avisos = traducir(cv, llm_marca)
    assert en.resumen == "EN:Hola mundo" and en.titular == f"EN:{cv.titular}"
    assert en.experiencia[0].logros == [f"EN:{x}" for x in cv.experiencia[0].logros]
    # No se tocan nombres propios, tecnologías, enlaces ni lo que se oculta o se incluye.
    assert en.nombre == cv.nombre and en.contacto == cv.contacto
    assert en.experiencia[0].organizacion == cv.experiencia[0].organizacion
    assert en.experiencia[0].tecnologias == cv.experiencia[0].tecnologias
    assert en.ocultas == ["referencias"] and avisos == []


def test_traduce_fechas_y_deja_vacio_lo_que_no_hay():
    cv = _cv()
    cv.experiencia[0].desde = "Septiembre 2025"
    cv.experiencia[0].proyecto = None
    en, _ = traducir(cv, llm_marca)
    assert en.experiencia[0].desde == "September 2025" and en.experiencia[0].hasta == cv.experiencia[0].hasta
    assert en.experiencia[0].proyecto is None


def test_si_el_modelo_pierde_la_cuenta_se_traduce_uno_a_uno():
    llamadas = []

    def llm(prompt, esquema):
        textos = _prompt_textos(prompt)
        llamadas.append(len(textos))
        return {"traducciones": ["x"] if len(textos) > 1 else [f"EN:{textos[0]}"]}

    en, avisos = traducir(_cv(), llm)
    assert en.resumen.startswith("EN:") and avisos == [] and 1 in llamadas


def test_si_cambia_una_cifra_se_deja_el_original_y_se_avisa():
    cv = _cv(resumen="Más de 2 años de experiencia")

    def llm(prompt, esquema):
        return {"traducciones": [t.replace("2", "3") if "años" in t else f"EN:{t}" for t in _prompt_textos(prompt)]}

    en, avisos = traducir(cv, llm)
    assert en.resumen == "Más de 2 años de experiencia"
    assert avisos == ["no-traducido:1"]


def test_un_fallo_del_modelo_es_un_error_claro():
    def roto(prompt, esquema):
        raise OSError("sin ollama")

    with pytest.raises(TraduccionError):
        traducir(_cv(), roto)


def test_endpoint_traduce_y_exige_clave(tmp_path):
    ajustes = Ajustes(CLAVE, tmp_path / "e.db", llm_traducir=llm_marca)
    c = TestClient(crear_app(ajustes))
    cuerpo = {"cv": _cv().model_dump(mode="json")}
    assert c.post("/v1/translate", json=cuerpo).status_code == 401
    r = c.post("/v1/translate", json=cuerpo, headers={"X-Api-Key": CLAVE})
    assert r.status_code == 200 and r.json()["cv"]["titular"].startswith("EN:") and r.json()["avisos"] == []


def test_endpoint_responde_502_si_el_modelo_falla(tmp_path):
    def roto(prompt, esquema):
        raise OSError("sin ollama")

    c = TestClient(crear_app(Ajustes(CLAVE, tmp_path / "e.db", llm_traducir=roto)))
    r = c.post("/v1/translate", json={"cv": _cv().model_dump(mode="json")}, headers={"X-Api-Key": CLAVE})
    assert r.status_code == 502 and r.json()["detail"] == "ia-fallo"


def test_render_acepta_idioma(tmp_path):
    vistos = []

    def compilador(tex: Path) -> Path:
        vistos.append(tex.read_text("utf-8"))
        pdf = tex.with_suffix(".pdf")
        pdf.write_bytes(b"%PDF-falso")
        return pdf

    c = TestClient(crear_app(Ajustes(CLAVE, tmp_path / "e.db", compilador=compilador)))
    cuerpo = {"cv": _cv().model_dump(mode="json"), "idioma": "en"}
    assert c.post("/v1/render", json=cuerpo, headers={"X-Api-Key": CLAVE}).status_code == 200
    assert r"\section*{Work Experience}" in vistos[0]
    cuerpo["idioma"] = "fr"
    assert c.post("/v1/render", json=cuerpo, headers={"X-Api-Key": CLAVE}).status_code == 422


def test_las_marcas_de_enfasis_se_conservan_en_la_traduccion():
    cv = _cv(resumen="Experto en **FastAPI** y Celery")

    def llm(prompt, esquema):
        return {"traducciones": [t.replace("Experto en **FastAPI** y", "Expert in **FastAPI** and") if "FastAPI" in t else f"EN:{t}"
                                 for t in _prompt_textos(prompt)]}

    en, avisos = traducir(cv, llm)
    assert en.resumen == "Expert in **FastAPI** and Celery" and avisos == []


def test_si_la_traduccion_pierde_una_marca_se_deja_el_original():
    cv = _cv(resumen="Experto en **FastAPI**")

    def llm(prompt, esquema):
        return {"traducciones": [t.replace("**", "") if "**" in t else f"EN:{t}" for t in _prompt_textos(prompt)]}

    en, avisos = traducir(cv, llm)
    assert en.resumen == "Experto en **FastAPI**" and avisos == ["no-traducido:1"]
