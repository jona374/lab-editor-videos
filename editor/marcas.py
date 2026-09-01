"""Carpetas por marca, tal como manda INSTRUCCIONES.md."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import RAIZ, SALIDAS
from .utilidades import es_video

SUBCARPETAS = ("videos-por-editar", "videos-listos", "tomas-de-apoyo")


@dataclass
class Marca:
    nombre: str
    carpeta: Path

    @property
    def por_editar(self) -> Path:
        return self.carpeta / "videos-por-editar"

    @property
    def listos(self) -> Path:
        return self.carpeta / "videos-listos"

    @property
    def tomas_de_apoyo(self) -> Path:
        return self.carpeta / "tomas-de-apoyo"

    @property
    def prompt(self) -> Path:
        return self.carpeta / "prompt.md"

    @property
    def salidas(self) -> Path:
        return SALIDAS / self.nombre

    def texto_prompt(self) -> str:
        """El prompt.md de la marca: tono, colores, CTA... Vacío si no hay nada útil."""
        if not self.prompt.exists():
            return ""
        texto = self.prompt.read_text(encoding="utf-8").strip()
        # La plantilla vacía que trae el repo no aporta nada al guion.
        return "" if "completa este archivo" in texto.lower() else texto

    def clips(self) -> list[Path]:
        return sorted(p for p in self.por_editar.glob("*") if p.is_file() and es_video(p))

    def clips_de_apoyo(self) -> list[Path]:
        if not self.tomas_de_apoyo.exists():
            return []
        return sorted(p for p in self.tomas_de_apoyo.glob("*") if p.is_file() and es_video(p))

    def preparar(self) -> "Marca":
        for sub in SUBCARPETAS:
            (self.carpeta / sub).mkdir(parents=True, exist_ok=True)
        self.salidas.mkdir(parents=True, exist_ok=True)
        if not self.prompt.exists():
            self.prompt.write_text(
                f"# Prompt de edición — {self.nombre}\n\n"
                "(Escribe aquí el estilo de esta marca: tono de voz, a quién le habla,\n"
                "qué NO decir, colores, música, y el CTA con el que cierra cada video.)\n",
                encoding="utf-8",
            )
        return self


def listar(raiz: Path = RAIZ) -> list[Marca]:
    """Toda carpeta de primer nivel con 'videos-por-editar' dentro es una marca."""
    marcas = []
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if (carpeta / "videos-por-editar").is_dir():
            marcas.append(Marca(carpeta.name, carpeta))
    return marcas


def obtener(nombre: str, raiz: Path = RAIZ, crear: bool = False) -> Marca:
    carpeta = raiz / nombre
    if not carpeta.is_dir() and not crear:
        conocidas = ", ".join(m.nombre for m in listar(raiz)) or "ninguna todavía"
        raise ValueError(f"no existe la marca {nombre!r}. Marcas: {conocidas}")
    return Marca(nombre, carpeta).preparar()
