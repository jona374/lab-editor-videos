"""Render con ffmpeg: cortes -> concatenado -> voz + música + subtítulos."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .config import Ajustes
from .corte import Segmento
from .utilidades import ffmpeg, tiene_audio

log = logging.getLogger("editor")

VIDEO = ("-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p")
AUDIO = ("-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2")


def recortar_segmentos(segmentos: list[Segmento], temporal: Path, ajustes: Ajustes) -> list[Path]:
    """Corta cada trozo y lo normaliza a la misma resolución, fps y códecs.

    Todos salen con pista de audio (silencio si el clip no traía) para que el
    concatenado posterior pueda hacerse por copia, sin recomprimir.
    """
    ancho, alto = ajustes.resolucion
    escalado = (
        f"scale={ancho}:{alto}:force_original_aspect_ratio=increase,"
        f"crop={ancho}:{alto},fps={ajustes.fps},setsar=1,format=yuv420p"
    )
    con_audio: dict[Path, bool] = {}
    partes = []

    for numero, segmento in enumerate(segmentos):
        destino = temporal / f"corte-{numero:03d}.mp4"
        if segmento.ruta not in con_audio:
            con_audio[segmento.ruta] = tiene_audio(segmento.ruta)
        origen_audio = "0:a:0" if con_audio[segmento.ruta] else "1:a:0"
        ffmpeg(
            "-ss", f"{segmento.inicio:.3f}", "-i", segmento.ruta,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{segmento.duracion:.3f}",
            "-map", "0:v:0", "-map", origen_audio,
            "-vf", escalado, *VIDEO, *AUDIO, "-shortest",
            destino,
            descripcion=f"corte {numero} de {segmento.ruta.name}",
        )
        partes.append(destino)
    return partes


def concatenar(partes: list[Path], destino: Path) -> Path:
    """Une los cortes por copia (rápido: no recomprime)."""
    lista = destino.parent / "lista-cortes.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    ffmpeg(
        "-f", "concat", "-safe", "0", "-i", lista.name, "-c", "copy", destino.name,
        descripcion="unir los cortes", cwd=destino.parent,
    )
    return destino


def montar(
    video_mudo: Path,
    destino: Path,
    ajustes: Ajustes,
    duracion_final: float,
    voz: Path | None = None,
    musica: Path | None = None,
    subtitulos_ass: Path | None = None,
) -> Path:
    """Pasada final: pega la voz, mete la música por debajo y quema los subtítulos.

    Se ejecuta con el directorio de trabajo en `destino.parent` para que el filtro
    de subtítulos reciba un nombre a secas y no haya que escapar la ruta.
    """
    # Se corre con cwd en destino.parent, así que las entradas van en absoluto.
    entradas: list[str | Path] = ["-i", video_mudo.resolve()]
    siguiente_indice = 1
    filtros: list[str] = []
    pistas: list[str] = []

    if subtitulos_ass is not None:
        if subtitulos_ass.parent != destino.parent:
            subtitulos_ass = Path(shutil.copy(subtitulos_ass, destino.parent / subtitulos_ass.name))
        filtros.append(f"[0:v]subtitles={subtitulos_ass.name}[v]")
        salida_video = "[v]"
    else:
        salida_video = "0:v"

    hay_musica = musica is not None and ajustes.volumen_musica > 0

    if voz is not None:
        entradas += ["-i", voz.resolve()]
        cadena_voz = f"[{siguiente_indice}:a]aformat=sample_rates=44100:channel_layouts=stereo,apad"
        # Si hay música, la voz se duplica: una copia suena y la otra sirve de
        # llave para el ducking (una etiqueta de filtro solo se consume una vez).
        filtros.append(cadena_voz + (",asplit=2[voz][voz_llave]" if hay_musica else "[voz]"))
        pistas.append("[voz]")
        siguiente_indice += 1

    if hay_musica:
        entradas += ["-stream_loop", "-1", "-i", musica.resolve()]
        desvanecido = max(0.0, duracion_final - 1.5)
        filtros.append(
            f"[{siguiente_indice}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"atrim=0:{duracion_final:.3f},asetpts=N/SR/TB,"
            f"afade=t=in:st=0:d=0.8,afade=t=out:st={desvanecido:.3f}:d=1.5,"
            f"volume={ajustes.volumen_musica}[musica]"
        )
        siguiente_indice += 1
        if voz is not None:
            # La música se agacha sola cuando habla la voz (ducking).
            filtros.append(
                "[musica][voz_llave]sidechaincompress="
                "threshold=0.04:ratio=8:attack=15:release=350[musica_baja]"
            )
            pistas.append("[musica_baja]")
        else:
            pistas.append("[musica]")

    if ajustes.volumen_clips > 0:
        filtros.append(f"[0:a]volume={ajustes.volumen_clips}[ambiente]")
        pistas.append("[ambiente]")

    if len(pistas) > 1:
        filtros.append(
            "".join(pistas) + f"amix=inputs={len(pistas)}:normalize=0:dropout_transition=0[audio]"
        )
        salida_audio: str | None = "[audio]"
    else:
        salida_audio = pistas[0] if pistas else None

    orden: list[str | Path] = [*entradas]
    if filtros:
        orden += ["-filter_complex", ";".join(filtros)]
    orden += ["-map", salida_video]
    orden += ["-map", salida_audio] if salida_audio else ["-an"]
    orden += ["-t", f"{duracion_final:.3f}"]
    # Si no hay subtítulos que quemar, el video ya está listo: se copia tal cual.
    orden += ["-c:v", "copy"] if subtitulos_ass is None else list(VIDEO)
    if salida_audio:
        orden += list(AUDIO)
    orden += ["-movflags", "+faststart", destino.name]

    ffmpeg(*orden, descripcion="montaje final", cwd=destino.parent)
    return destino
