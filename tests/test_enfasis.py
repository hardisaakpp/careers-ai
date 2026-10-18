from careers_ai.carta import redactar
from careers_ai.enfasis import a_latex, sin_enfasis
from careers_ai.modelos import Oferta
from tests.test_traducir import _cv


def test_a_latex_convierte_solo_pares_completos():
    assert a_latex("a **b** c") == r"a \textbf{b} c"
    assert a_latex("**a** y **b**") == r"\textbf{a} y \textbf{b}"
    assert a_latex("sin marcas") == "sin marcas"


def test_marcas_con_espacios_pegados_no_resaltan():
    assert a_latex("a ** b ** c") == "a  b  c"


def test_el_enfasis_no_cruza_lineas():
    assert a_latex("**a\nb**") == "a\nb"


def test_sin_enfasis_quita_las_marcas():
    assert sin_enfasis("Experto en **FastAPI** y **Celery**") == "Experto en FastAPI y Celery"
    assert sin_enfasis("suelto ** aquí") == "suelto  aquí"


def test_la_carta_no_lleva_marcas():
    cv = _cv(resumen="Construyo **APIs REST** con Python")
    carta = redactar(cv, Oferta(id="1", titulo="Backend", empresa="Acme", descripcion=""))
    assert "**" not in carta and "APIs REST" in carta
