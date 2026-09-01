"""Prueba de punta a punta: clips de mentira -> video real. Necesita ffmpeg."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from editor import marcas, pipeline, voz as voces
from editor.config import Ajustes
from editor.marcas import Marca
from editor.subtitulos import Palabra
from editor.utilidades import duracion, ffmpeg

GUION = "Esto frena el scroll. Aquí va el dato duro. Escríbenos por WhatsApp."

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="hace falta ffmpeg")


def _clip(destino: Path, segundos: float, patron: str = "testsrc", con_audio: bool = True) -> Path:
    orden = ["-f", "lavfi", "-i", f"{patron}=size=320x568:rate=15"]
    if con_audio:
        orden += ["-f", "lavfi", "-i", "sine=frequency=300"]
    orden += ["-t", str(segundos), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if con_audio:
        orden += ["-c:a", "aac", "-shortest"]
    ffmpeg(*orden, destino)
    return destino


@pytest.fixture
def marca(tmp_path, monkeypatch) -> Marca:
    """Una marca de mentira, con sus carpetas, fuera del repo."""
    carpeta = tmp_path / "marca-prueba"
    monkeypatch.setattr(marcas, "SALIDAS", tmp_path / "salidas")
    monkeypatch.setattr(pipeline.marcas, "obtener", lambda nombre, **_: Marca(nombre, carpeta).preparar())
    creada = Marca("marca-prueba", carpeta).preparar()
    _clip(creada.por_editar / "uno.mp4", 4)
    _clip(creada.por_editar / "dos.mp4", 3, patron="smptebars", con_audio=False)
    _clip(creada.tomas_de_apoyo / "apoyo.mp4", 3, patron="testsrc2")
    return creada


def test_video_sin_voz_dura_lo_pedido_y_deja_los_archivos(marca, monkeypatch):
    monkeypatch.setattr(pipeline.musicas, "elegir", lambda *a, **k: None)
    ajustes = Ajustes(marca=marca.nombre, duracion_objetivo=6, duracion_corte=2, semilla=1)

    resultado = pipeline.crear_video(ajustes, texto_guion=GUION, sin_voz=True, avisar=lambda _: None)

    assert duracion(resultado.video) == pytest.approx(6, abs=0.3)
    assert (resultado.carpeta / "guion.md").exists()
    assert (resultado.carpeta / "plan.json").exists()
    assert resultado.subtitulos.read_text(encoding="utf-8").startswith("1\n00:00:00,000")
    assert resultado.copia_en_marca.exists()  # queda en videos-listos/
    assert len(resultado.segmentos) == 3


def test_con_voz_el_video_se_alarga_para_que_no_se_corte(marca, monkeypatch, tmp_path):
    pista = tmp_path / "voz.mp3"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=440", "-t", "9", pista)
    palabras = [Palabra(p, i * 0.5, i * 0.5 + 0.45) for i, p in enumerate(GUION.split())]
    monkeypatch.setattr(
        pipeline.voces, "generar",
        lambda texto, destino, ajustes: voces.Locucion(shutil.copy(pista, destino) and destino, 9.0, palabras),
    )
    monkeypatch.setattr(pipeline.musicas, "elegir", lambda *a, **k: None)
    ajustes = Ajustes(marca=marca.nombre, duracion_objetivo=6, duracion_corte=2, cola_silencio=0.6)

    resultado = pipeline.crear_video(ajustes, texto_guion=GUION, avisar=lambda _: None)

    assert duracion(resultado.video) == pytest.approx(9.6, abs=0.4)
    assert resultado.voz and resultado.voz.exists()


def test_sin_clips_el_error_dice_dónde_subirlos(marca, monkeypatch):
    for clip in marca.clips():
        clip.unlink()
    ajustes = Ajustes(marca=marca.nombre, duracion_objetivo=6)
    with pytest.raises(ValueError, match="videos-por-editar"):
        pipeline.crear_video(ajustes, texto_guion=GUION, sin_voz=True, avisar=lambda _: None)
