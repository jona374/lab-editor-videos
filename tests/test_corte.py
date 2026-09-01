from pathlib import Path

import pytest

from editor.corte import Clip, plan_de_corte


def clips(*duraciones: float) -> list[Clip]:
    return [Clip(Path(f"clip{i}.mp4"), d) for i, d in enumerate(duraciones)]


def test_la_suma_de_los_cortes_da_la_duracion_pedida():
    segmentos = plan_de_corte(clips(10, 10, 10), duracion_total=46, duracion_corte=2)
    assert sum(s.duracion for s in segmentos) == pytest.approx(46)
    assert len(segmentos) == 23


def test_el_ultimo_corte_se_recorta_para_cuadrar():
    segmentos = plan_de_corte(clips(10, 10), duracion_total=45, duracion_corte=2)
    assert segmentos[-1].duracion == pytest.approx(1.0)
    assert all(s.duracion == 2 for s in segmentos[:-1])


def test_alterna_entre_clips_en_vez_de_vaciar_uno():
    segmentos = plan_de_corte(clips(30, 30, 30), duracion_total=12, duracion_corte=2, semilla=1)
    assert all(a.ruta != b.ruta for a, b in zip(segmentos, segmentos[1:]))


def test_reutiliza_material_cuando_no_alcanza():
    segmentos = plan_de_corte(clips(4), duracion_total=10, duracion_corte=2)
    assert sum(s.duracion for s in segmentos) == pytest.approx(10)
    assert {s.ruta.name for s in segmentos} == {"clip0.mp4"}
    assert segmentos[0].inicio == 0 and segmentos[2].inicio == 0  # rebobinó al acabarse


def test_los_cortes_nunca_se_salen_del_clip():
    duraciones = {Path("clip0.mp4"): 7, Path("clip1.mp4"): 3}
    segmentos = plan_de_corte(clips(7, 3), duracion_total=30, duracion_corte=2)
    assert all(s.fin <= duraciones[s.ruta] + 1e-6 for s in segmentos)


def test_mete_tomas_de_apoyo_cada_n_cortes():
    apoyos = [Clip(Path("apoyo.mp4"), 8, apoyo=True)]
    segmentos = plan_de_corte(clips(20, 20), duracion_total=12, duracion_corte=2,
                              apoyos=apoyos, proporcion_apoyos=3)
    assert [s.apoyo for s in segmentos] == [False, False, True, False, False, True]


def test_la_semilla_repite_el_mismo_plan():
    uno = plan_de_corte(clips(20, 20, 20), 20, 2, semilla=7)
    otro = plan_de_corte(clips(20, 20, 20), 20, 2, semilla=7)
    assert uno == otro


def test_sin_clips_avisa_claro():
    with pytest.raises(ValueError, match="videos-por-editar"):
        plan_de_corte([], duracion_total=46)


def test_clips_mas_cortos_que_el_corte_igual_producen_video():
    segmentos = plan_de_corte(clips(1.2, 1.2), duracion_total=6, duracion_corte=2)
    assert sum(s.duracion for s in segmentos) == pytest.approx(6)
