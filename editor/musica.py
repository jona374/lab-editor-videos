"""Elección de la pista de música de fondo desde assets/musica/."""

from __future__ import annotations

import random
from pathlib import Path

from .config import MUSICA
from .utilidades import es_audio


def moods(carpeta: Path = MUSICA) -> list[str]:
    """Las subcarpetas de assets/musica son los ambientes: energico, calmado..."""
    if not carpeta.exists():
        return []
    return sorted(p.name for p in carpeta.iterdir() if p.is_dir() and any(map(es_audio, p.glob("*"))))


def pistas(carpeta: Path = MUSICA) -> list[Path]:
    if not carpeta.exists():
        return []
    return sorted(p for p in carpeta.rglob("*") if p.is_file() and es_audio(p))


def elegir(preferencia: str | None, mood: str | None = None, carpeta: Path = MUSICA,
           semilla: int | None = None) -> Path | None:
    """Busca la pista: primero lo que pidió el usuario, luego el mood del guion.

    `preferencia` puede ser una ruta, un nombre de archivo o un nombre de carpeta.
    Devuelve None si no hay música (el video sale solo con la voz).
    """
    disponibles = pistas(carpeta)
    if not disponibles:
        return None
    azar = random.Random(semilla)

    for candidato in (preferencia, mood):
        if not candidato:
            continue
        ruta = Path(candidato)
        if ruta.is_file():
            return ruta
        clave = candidato.strip().lower()
        coincidencias = [
            p for p in disponibles
            if clave in p.name.lower() or clave in {parte.lower() for parte in p.parent.parts}
        ]
        if coincidencias:
            return azar.choice(coincidencias)

    return azar.choice(disponibles)
