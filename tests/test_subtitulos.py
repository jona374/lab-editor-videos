import pytest

from editor.subtitulos import (
    Palabra, a_ass, a_srt, agrupar, estimar_palabras, palabras_desde_alineacion,
)


def test_alineacion_de_elevenlabs_a_palabras():
    texto = "hola que tal"
    caracteres = list(texto)
    inicios = [i * 0.1 for i in range(len(texto))]
    fines = [i * 0.1 + 0.1 for i in range(len(texto))]

    palabras = palabras_desde_alineacion(caracteres, inicios, fines)

    assert [p.texto for p in palabras] == ["hola", "que", "tal"]
    assert palabras[0].inicio == pytest.approx(0.0)
    assert palabras[1].inicio == pytest.approx(0.5)
    assert palabras[-1].fin == pytest.approx(1.2)


def test_alineacion_descuadrada_avisa():
    with pytest.raises(ValueError):
        palabras_desde_alineacion(["a", "b"], [0.0], [0.1])


def test_estimacion_sin_voz_cubre_toda_la_duracion():
    palabras = estimar_palabras("Una frase corta para probar.", duracion=4)
    assert palabras[0].inicio == pytest.approx(0)
    assert palabras[-1].fin == pytest.approx(4)
    assert all(a.fin <= b.inicio + 1e-9 for a, b in zip(palabras, palabras[1:]))


def test_los_bloques_respetan_el_maximo_de_palabras_y_caracteres():
    palabras = [Palabra(f"palabra{i}", i * 0.4, i * 0.4 + 0.4) for i in range(12)]
    bloques = agrupar(palabras, max_caracteres=26, max_palabras=3)
    assert all(len(b.texto.split()) <= 3 for b in bloques)
    assert all(len(b.texto) <= 26 for b in bloques)


def test_una_pausa_larga_corta_el_bloque():
    palabras = [Palabra("uno", 0, 0.3), Palabra("dos", 1.5, 1.8)]
    assert len(agrupar(palabras)) == 2


def test_el_punto_final_cierra_el_bloque():
    palabras = [Palabra("uno.", 0, 0.3), Palabra("dos", 0.35, 0.6)]
    assert [b.texto for b in agrupar(palabras)] == ["uno.", "dos"]


def test_srt_con_formato_valido():
    srt = a_srt(agrupar([Palabra("hola", 0, 0.5)]))
    assert srt.startswith("1\n00:00:00,000 --> 00:00:00,500\nhola")


def test_ass_lleva_estilo_y_dialogos_en_mayusculas():
    ass = a_ass(agrupar([Palabra("hola", 0, 0.5)]), 1080, 1920)
    assert "[V4+ Styles]" in ass and "PlayResY: 1920" in ass
    assert "Dialogue: 0,0:00:00.00,0:00:00.50,Base,,0,0,0,,HOLA" in ass
