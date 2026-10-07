"""Años de experiencia que pide una oferta, y la regla «experiencia máxima»."""

import pytest

from careers_ai.modelos import Oferta
from careers_ai.ranking.nivel import anos_requeridos
from careers_ai.ranking.preferencias import Preferencias
from careers_ai.ranking.ranking import ordenar, regla_dura


@pytest.mark.parametrize("titulo,descripcion,esperado", [
    # por el título
    ("Senior .NET Full-stack Developer", "", 5),
    ("Sr. Backend Engineer", "", 5),
    ("Staff Engineer", "", 7),
    ("Principal Software Architect", "", 7),
    ("Engineering Manager", "", 7),
    ("Junior Backend Developer", "", 0),
    ("Software Engineering Intern", "", 0),
    ("Pasante de Desarrollo", "", 0),
    # por la descripción, en inglés y en español
    ("Full Stack Developer", "5+ years of professional experience in Python", 5),
    ("DESARROLLADOR FULL STACK", "Buscamos 3+ años de experiencia con Angular", 3),
    ("Developer", "Minimum of 4 years building APIs", 4),
    ("React Developer", "at least 6 years", 6),
    ("Backend Developer", "Experience: 3-5 years", 3),  # un rango: lo mínimo que piden
    ("Backend Developer", "3 to 5 years of experience", 3),
    ("Desarrollador", "de 2 a 4 años de experiencia", 2),
    # manda el indicio más exigente
    ("Junior Developer", "2+ years of experience", 2),
    ("Senior Developer", "2+ years of experience", 5),
    ("Developer", "5+ years of experience. 2+ years of experience with Docker", 5),
    # sin base para juzgar: None, nunca un 0 inventado
    ("Python Developer", "Great team, remote.", None),
    ("Backend Developer", "We are a company with 20 years of experience in logistics", None),  # habla de la empresa
    ("Developer", "3 years of Docker experience", None),  # experiencia en una tecnología, no un requisito general
    ("Leadership Coach", "", None),
])
def test_anos_requeridos(titulo, descripcion, esperado):
    assert anos_requeridos(titulo, descripcion) == esperado


def test_leader_no_se_confunde_con_lead_dentro_de_otra_palabra():
    assert anos_requeridos("Misleading title developer", "") is None
    assert anos_requeridos("Team Lead", "") == 7


def oferta(titulo, descripcion="", id="1"):
    return Oferta(id=id, titulo=titulo, empresa="Acme", descripcion=descripcion)


def test_sin_limite_no_se_descarta_nada_por_nivel():
    assert regla_dura(oferta("Staff Engineer"), Preferencias()) is None


def test_con_limite_se_descartan_las_que_piden_mas_y_se_dice_por_que():
    pref = Preferencias(max_anos=3)
    assert regla_dura(oferta("Senior Developer"), pref) == "pide 5 años de experiencia"
    assert regla_dura(oferta("Developer", "5+ years of experience"), pref) == "pide 5 años de experiencia"
    assert regla_dura(oferta("Developer", "3+ years of experience"), pref) is None  # justo en el límite: se queda
    assert regla_dura(oferta("Junior Developer"), pref) is None


def test_una_oferta_que_no_dice_su_nivel_no_se_descarta():
    assert regla_dura(oferta("Python Developer", "Remote team."), Preferencias(max_anos=1)) is None


def test_el_limite_cero_deja_solo_lo_que_no_pide_experiencia():
    pref = Preferencias(max_anos=0)
    assert regla_dura(oferta("Junior Developer"), pref) is None
    assert regla_dura(oferta("Developer", "1+ years of experience"), pref) == "pide 1 años de experiencia"


def test_el_limite_va_junto_a_las_otras_reglas_y_ordenar_deja_las_descartadas_al_final():
    from careers_ai.modelo import Cv

    cv = Cv.model_validate({"nombre": "A", "titular": "T", "resumen": "R", "contacto": {"email": "a@b.co"}})
    ofertas = [oferta("Senior Python Developer", id="s"), oferta("Python Developer", id="m"), oferta("Junior Python Developer", id="j")]
    res = ordenar(cv, ofertas, Preferencias(max_anos=2), lambda textos: [[1.0] for _ in textos])
    assert [r.oferta.id for r in res][-1] == "s"
    assert {r.oferta.id: r.excluida for r in res}["s"] == "pide 5 años de experiencia"
    assert all(r.excluida is None for r in res if r.oferta.id in ("m", "j"))


@pytest.mark.parametrize("valor", [-1, 31])
def test_el_limite_debe_ser_razonable(valor):
    with pytest.raises(Exception):
        Preferencias(max_anos=valor)
