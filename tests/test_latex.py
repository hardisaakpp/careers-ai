from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from careers_ai.latex import escapar, renderizar
from careers_ai.modelo import Cv

EJEMPLO = Path(__file__).parent.parent / "data" / "ejemplo.yaml"


def _cv(**cambios) -> Cv:
    datos = yaml.safe_load(EJEMPLO.read_text("utf-8"))
    datos.update(cambios)
    return Cv.model_validate(datos)


def test_escapa_caracteres_especiales():
    assert escapar("A & B 50% $x_1 #{}") == r"A \& B 50\% \$x\_1 \#\{\}"


def test_no_deja_pasar_comandos():
    s = escapar(r"\input{/etc/passwd}")
    assert s.startswith(r"\textbackslash{}input")
    assert "\\input" not in s.replace(r"\textbackslash{}", "")


def test_render_incluye_datos_y_escapa():
    tex = renderizar(_cv())
    assert r"Empresa Demo \& Co." in tex
    assert r"\begin{document}" in tex and r"\end{document}" in tex
    assert "2022-03 -- actual" in tex


def test_inyeccion_en_logro_no_llega_cruda():
    cv = _cv(resumen=r"\write18{rm -rf /} \input{x}")
    tex = renderizar(cv)
    assert r"\write18" not in tex and r"\input{x}" not in tex


def test_secciones_vacias_se_omiten():
    tex = renderizar(_cv(proyectos=[], educacion=[]))
    assert "Proyectos" not in tex and "Educación" not in tex


def test_modelo_rechaza_campos_desconocidos():
    with pytest.raises(ValidationError):
        _cv(salario_deseado=1)


def test_tecnologias_unificadas():
    assert {".NET", "Docker", "Next.js", "Python"} <= _cv().tecnologias()
