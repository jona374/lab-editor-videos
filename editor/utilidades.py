"""Envoltorios de ffmpeg y utilidades sueltas."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

log = logging.getLogger("editor")

EXTENSIONES_VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
EXTENSIONES_AUDIO = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}


class ErrorFfmpeg(RuntimeError):
    pass


def _binario(nombre: str) -> str:
    """Busca ffmpeg/ffprobe en el PATH, en las variables de entorno o en imageio-ffmpeg."""
    entorno = os.getenv(f"{nombre.upper()}_BIN")
    if entorno:
        return entorno
    encontrado = shutil.which(nombre)
    if encontrado:
        return encontrado
    if nombre == "ffmpeg":
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    raise ErrorFfmpeg(
        f"No encuentro '{nombre}'. Instálalo con 'apt install ffmpeg' (Linux), "
        "'brew install ffmpeg' (Mac) o apunta la variable "
        f"{nombre.upper()}_BIN al ejecutable."
    )


def ffmpeg(*args: str | Path, descripcion: str = "", cwd: Path | None = None) -> None:
    """Corre ffmpeg y revienta con el stderr si falla."""
    orden = [_binario("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)]
    log.debug("ffmpeg %s", " ".join(orden[1:]))
    proceso = subprocess.run(orden, capture_output=True, text=True, cwd=cwd)
    if proceso.returncode != 0:
        cola = proceso.stderr.strip().splitlines()[-12:]
        raise ErrorFfmpeg(f"falló ffmpeg{f' ({descripcion})' if descripcion else ''}:\n" + "\n".join(cola))


def sondear(ruta: Path) -> dict:
    """ffprobe -> dict con la info del archivo."""
    orden = [
        _binario("ffprobe"), "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(ruta),
    ]
    proceso = subprocess.run(orden, capture_output=True, text=True)
    if proceso.returncode != 0:
        raise ErrorFfmpeg(f"no pude leer {ruta.name}: {proceso.stderr.strip()}")
    return json.loads(proceso.stdout)


def duracion(ruta: Path) -> float:
    """Duración en segundos de un video o audio."""
    info = sondear(ruta)
    if "duration" in info.get("format", {}):
        return float(info["format"]["duration"])
    for flujo in info.get("streams", []):
        if "duration" in flujo:
            return float(flujo["duration"])
    raise ErrorFfmpeg(f"{ruta.name} no declara duración")


def tiene_audio(ruta: Path) -> bool:
    return any(f.get("codec_type") == "audio" for f in sondear(ruta).get("streams", []))


def es_video(ruta: Path) -> bool:
    return ruta.suffix.lower() in EXTENSIONES_VIDEO


def es_audio(ruta: Path) -> bool:
    return ruta.suffix.lower() in EXTENSIONES_AUDIO


def slug(texto: str, largo: int = 60) -> str:
    """'Camisa de trabajo ¡nueva!' -> 'camisa-de-trabajo-nueva'."""
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", plano).strip("-").lower()
    return (limpio[:largo].rstrip("-") or "video")


def formatear_tiempo(segundos: float, separador: str = ",") -> str:
    """46.5 -> '00:00:46,500' (SRT) o '0:00:46.50' con separador '.' para ASS."""
    segundos = max(0.0, segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    if separador == ",":
        return f"{int(horas):02d}:{int(minutos):02d}:{int(seg):02d},{int(round((seg % 1) * 1000)):03d}"
    return f"{int(horas):d}:{int(minutos):02d}:{int(seg):02d}.{int((seg % 1) * 100):02d}"
