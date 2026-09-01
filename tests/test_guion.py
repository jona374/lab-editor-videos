from editor.config import Ajustes
from editor.guion import Guion, desde_texto


def test_guion_manual_reparte_gancho_cuerpo_y_cta():
    guion = desde_texto("Esto frena el scroll. Aquí va el dato. Escríbeme por WhatsApp.")
    assert guion.gancho == "Esto frena el scroll."
    assert guion.cuerpo == ["Aquí va el dato."]
    assert guion.cta == "Escríbeme por WhatsApp."


def test_la_narracion_junta_todo_en_una_sola_linea():
    guion = Guion(titulo="t", gancho="Uno.", cuerpo=["Dos."], cta="Tres.")
    assert guion.narracion() == "Uno. Dos. Tres."
    assert guion.palabras() == 3


def test_las_palabras_objetivo_salen_de_la_duracion():
    assert Ajustes(marca="x", duracion_objetivo=46).palabras_objetivo == 126
    assert Ajustes(marca="x", duracion_objetivo=60).palabras_objetivo == 165


def test_el_markdown_del_guion_incluye_las_tomas_de_apoyo():
    guion = Guion(titulo="t", gancho="g", cta="c", tomas_de_apoyo=["manos cosiendo"])
    assert "manos cosiendo" in guion.a_markdown()
