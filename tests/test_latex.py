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


def _pdf(**cambios) -> str:
    return renderizar(_cv(**cambios))


def test_secciones_nuevas_se_renderizan():
    tex = _pdf(
        certificaciones=[{"nombre": "Scrum Foundation", "emisor": "Certiprof", "anio": "2024"}],
        idiomas=[{"nombre": "Inglés", "nivel": "B2"}],
        investigacion=[{"cargo": "Investigador", "organizacion": "Smart Lab", "desde": "2025-10",
                        "ubicacion": "Quito, Ecuador", "logros": ["Pipeline RAG"]}],
    )
    assert "Scrum Foundation" in tex and "Certiprof" in tex
    assert "Inglés" in tex and "B2" in tex
    assert "Smart Lab" in tex and "Quito, Ecuador" in tex and "Pipeline RAG" in tex


def test_entrada_desactivada_no_sale_en_el_pdf_pero_se_conserva():
    cv = _cv(idiomas=[{"nombre": "Inglés", "nivel": "B2"}, {"nombre": "Klingon", "incluir": False}])
    tex = renderizar(cv)
    assert "Inglés" in tex and "Klingon" not in tex
    assert len(cv.idiomas) == 2


def test_seccion_oculta_no_sale_en_el_pdf():
    base = _cv()
    cv = base.model_copy(update={
        "contacto": base.contacto.model_copy(update={"telefono": "+593 962567643"}),
        "ocultas": ["resumen", "proyectos", "contacto.telefono"],
    })
    assert "+593 962567643" in renderizar(cv.model_copy(update={"ocultas": []}))
    tex = renderizar(cv)
    assert "Perfil profesional" not in tex and "Proyectos" not in tex
    assert "+593 962567643" not in tex


def test_entrada_incluida_por_defecto():
    assert _cv(idiomas=[{"nombre": "Inglés"}]).idiomas[0].incluir is True


def test_un_estudio_sin_fechas_no_muestra_un_actual_falso():
    tex = _pdf(educacion=[{"titulo": "Curso de Linux", "institucion": "Academia", "desde": ""}])
    assert "Curso de Linux" in tex and "-- actual" not in tex.split("Curso de Linux")[1].split("Academia")[0]


def test_las_referencias_solo_salen_si_estan_activadas():
    cv = _cv(referencias=[{"nombre": "Luis Perez", "cargo": "Jefe", "contacto": "099"}])
    assert "Luis Perez" in renderizar(cv)
    assert "Luis Perez" not in renderizar(cv.model_copy(update={"ocultas": ["referencias"]}))


# ---------- encabezado con iconos ----------

from careers_ai.latex import info_enlace, linea_contacto  # noqa: E402


@pytest.mark.parametrize("etiqueta,url,icono,texto", [
    ("GitHub", "https://github.com/usuario-demo", r"\faGithub", "usuario-demo"),
    ("GitHub", "https://www.github.com/usuario-demo/repo", r"\faGithub", "usuario-demo"),
    ("LinkedIn", "https://www.linkedin.com/in/usuario-demo/", r"\faLinkedin", "usuario-demo"),
    ("LinkedIn", "https://linkedin.com/company/acme", r"\faLinkedin", "acme"),
    ("LinkedIn", "https://linkedin.com/", r"\faLinkedin", "LinkedIn"),  # sin usuario: la etiqueta
    ("Portafolio", "https://ana.example.com", r"\faGlobe", "Portafolio"),
    ("", "https://ana.example.com/cv", r"\faGlobe", "ana.example.com"),
    ("Mi sitio", "no es una url", r"\faGlobe", "Mi sitio"),
    ("X", "http://[", r"\faGlobe", "X"),  # dirección rota: no debe lanzar
])
def test_cada_enlace_recibe_su_icono_y_se_muestra_el_usuario(etiqueta, url, icono, texto):
    assert info_enlace(etiqueta, url) == (icono, texto)


def _con_contacto(**c) -> Cv:
    base = _cv()
    return base.model_copy(update={"contacto": base.contacto.model_copy(update=c)})


def test_encabezado_con_iconos_por_defecto():
    cv = _con_contacto(telefono="+593 99", ubicacion="Quito",
                       enlaces={"GitHub": "https://github.com/usuario-demo"})
    linea = linea_contacto(cv, iconos=True)
    assert r"\faPhone" in linea and r"\faEnvelope" in linea and r"\faGithub\ usuario-demo" in linea
    assert linea.endswith("Quito")  # la ubicación va al final y sin icono, como en el CV de referencia
    assert r"\faGithub" in renderizar(cv)


def test_el_interruptor_quita_los_iconos_y_vuelve_a_la_etiqueta():
    cv = _con_contacto(enlaces={"GitHub": "https://github.com/usuario-demo"})
    tex = renderizar(cv.model_copy(update={"ocultas": ["contacto.iconos"]}))
    assert r"\faGithub" not in tex and r"\faEnvelope" not in tex
    assert r"{GitHub}" in tex  # el texto del enlace es la etiqueta, no el usuario


def test_un_dato_de_contacto_oculto_no_deja_su_icono():
    cv = _con_contacto(telefono="+593 99").model_copy(update={"ocultas": ["contacto.telefono"]})
    assert r"\faPhone" not in renderizar(cv)


def test_el_texto_del_encabezado_sigue_escapado_aunque_haya_iconos():
    cv = _con_contacto(telefono=r"\input{/etc/passwd}", enlaces={r"\write18{x}": "https://ana.example.com/a_b%20c"})
    linea = linea_contacto(cv, iconos=True)
    assert "\\input{" not in linea.replace(r"\textbackslash{}", "") and "\\write18{" not in linea.replace(r"\textbackslash{}", "")
    assert r"a\_b\%20c" in linea


def test_el_pdf_usa_la_tipografia_compacta_sans_serif():
    tex = renderizar(_cv())
    assert r"\documentclass[9pt,a4paper]{extarticle}" in tex
    assert r"\usepackage{carlito}" in tex and r"\familydefault}{\sfdefault}" in tex
    assert r"\LARGE" not in tex  # el nombre ya no es de 25 pt


@pytest.mark.parametrize("etiqueta,url,texto", [
    # Lo que la persona escribe en la etiqueta es lo que se muestra, sea cual sea la dirección…
    ("CarlosOrtiz", "https://github.com/hardisaakpp", "CarlosOrtiz"),
    ("carlosortiz", "https://www.linkedin.com/in/isaac-ortiz-581529169/", "carlosortiz"),
    ("Mi portafolio", "https://ana.example.com", "Mi portafolio"),
    # …y solo si es el nombre del sitio, o está vacía, se usa el usuario de la dirección.
    ("LinkedIn", "https://www.linkedin.com/in/isaac-ortiz-581529169/", "isaac-ortiz-581529169"),
    ("  github ", "https://github.com/hardisaakpp", "hardisaakpp"),
    ("", "https://github.com/hardisaakpp", "hardisaakpp"),
])
def test_la_etiqueta_que_escribe_la_persona_manda_sobre_la_direccion(etiqueta, url, texto):
    assert info_enlace(etiqueta, url)[1] == texto


def _exp(n: int):
    return [{"cargo": f"Cargo {i}", "organizacion": f"Empresa {i}", "desde": "2020"} for i in range(n)]


def test_hay_espacio_entre_una_experiencia_y_la_siguiente_pero_no_despues_de_la_ultima():
    sep = r"\par\vspace{\entradagap}"
    sin_otras = {"proyectos": [], "educacion": [], "investigacion": []}
    assert renderizar(_cv(experiencia=_exp(1), **sin_otras)).count(sep) == 0
    assert renderizar(_cv(experiencia=_exp(2), **sin_otras)).count(sep) == 1
    assert renderizar(_cv(experiencia=_exp(4), **sin_otras)).count(sep) == 3


def test_estudios_y_proyectos_se_separan_igual_que_las_experiencias():
    sep = r"\par\vspace{\entradagap}"
    estudios = [{"titulo": f"T{i}", "institucion": f"I{i}", "desde": "2010"} for i in range(3)]
    proyectos = [{"nombre": f"P{i}", "descripcion": "d"} for i in range(3)]
    tex = renderizar(_cv(experiencia=[], investigacion=[], educacion=estudios, proyectos=proyectos))
    assert tex.count(sep) == 4  # 2 entre estudios + 2 entre proyectos


def test_la_investigacion_con_proyecto_lo_pone_en_negrita_con_la_organizacion_entre_parentesis():
    tex = _pdf(investigacion=[{"cargo": "Investigador", "organizacion": "Escuela Politécnica Nacional", "desde": "2025-10",
                               "proyecto": "Smart Lab: ciberseguridad e IoT", "logros": ["Orquestador de IA"]}])
    assert r"\textbf{Smart Lab: ciberseguridad e IoT} (Escuela Politécnica Nacional)" in tex
    assert r"\textbf{Escuela Politécnica Nacional}" not in tex


def test_sin_proyecto_la_organizacion_sigue_encabezando_la_entrada():
    tex = _pdf(investigacion=[{"cargo": "Investigador", "organizacion": "Smart Lab", "desde": "2025-10"}])
    assert r"\textbf{Smart Lab}" in tex and "(Smart Lab)" not in tex


def test_el_idioma_cambia_los_rotulos_y_actual():
    es, en = renderizar(_cv()), renderizar(_cv(), idioma="en")
    assert r"\section*{Experiencia laboral}" in es and r"\section*{Work Experience}" in en
    assert "2022-03 -- actual" in es and "2022-03 -- Present" in en
    assert "Perfil profesional" not in en


def test_idioma_desconocido_se_rechaza():
    with pytest.raises(ValueError):
        renderizar(_cv(), idioma="fr")


def test_lo_marcado_sale_en_negrita_y_lo_demas_no():
    cv = _cv(resumen="Experto en **FastAPI y Celery** con 5 años")
    tex = renderizar(cv)
    assert r"Experto en \textbf{FastAPI y Celery} con 5 años" in tex


def test_el_enfasis_se_escapa_antes_de_convertirse():
    tex = renderizar(_cv(resumen=r"**A & B** y **\input{x}**"))
    assert r"\textbf{A \& B}" in tex and r"\input{x}" not in tex.replace(r"\textbackslash{}", "")


def test_una_marca_sin_pareja_no_llega_al_pdf():
    tex = renderizar(_cv(resumen="Uno ** suelto y **otro sin cerrar"))
    assert "**" not in tex
