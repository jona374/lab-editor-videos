"""De la voz a subtítulos: palabras con tiempos -> bloques -> .srt y .ass."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .utilidades import formatear_tiempo


@dataclass(frozen=True)
class Palabra:
    texto: str
    inicio: float
    fin: float


@dataclass
class Bloque:
    """Lo que se ve en pantalla de una vez (2-4 palabras, estilo TikTok)."""

    texto: str
    inicio: float
    fin: float


def palabras_desde_alineacion(caracteres: list[str], inicios: list[float], fines: list[float]) -> list[Palabra]:
    """Convierte la alineación por carácter de ElevenLabs en palabras."""
    if not (len(caracteres) == len(inicios) == len(fines)):
        raise ValueError("la alineación de ElevenLabs viene descuadrada")

    palabras: list[Palabra] = []
    actual, arranque, ultimo_fin = "", None, 0.0
    for caracter, inicio, fin in zip(caracteres, inicios, fines):
        if caracter.isspace():
            if actual:
                palabras.append(Palabra(actual, arranque, ultimo_fin))
                actual, arranque = "", None
            continue
        if arranque is None:
            arranque = inicio
        actual += caracter
        ultimo_fin = fin
    if actual:
        palabras.append(Palabra(actual, arranque or 0.0, ultimo_fin))
    return palabras


def estimar_palabras(texto: str, duracion: float, inicio: float = 0.0) -> list[Palabra]:
    """Reparte el texto en el tiempo sin alineación real (modo borrador, sin voz).

    Da más tiempo a las palabras largas y suma una pausa extra tras cada signo.
    """
    crudas = [p for p in re.split(r"\s+", texto.strip()) if p]
    if not crudas or duracion <= 0:
        return []

    pesos = [len(p) + (3 if p[-1] in ".,;:!?" else 0) for p in crudas]
    total = sum(pesos)
    palabras, reloj = [], inicio
    for palabra, peso in zip(crudas, pesos):
        largo = duracion * peso / total
        palabras.append(Palabra(palabra, reloj, reloj + largo))
        reloj += largo
    return palabras


def agrupar(
    palabras: list[Palabra],
    max_caracteres: int = 26,
    max_palabras: int = 4,
    max_duracion: float = 2.2,
    corte_por_pausa: float = 0.45,
) -> list[Bloque]:
    """Junta palabras en bloques cortos, respetando pausas y signos de puntuación."""
    bloques: list[Bloque] = []
    grupo: list[Palabra] = []

    def cerrar() -> None:
        if grupo:
            bloques.append(Bloque(" ".join(p.texto for p in grupo), grupo[0].inicio, grupo[-1].fin))
            grupo.clear()

    for palabra in palabras:
        if grupo:
            largo_texto = len(" ".join(p.texto for p in grupo)) + 1 + len(palabra.texto)
            pausa = palabra.inicio - grupo[-1].fin
            if (
                largo_texto > max_caracteres
                or len(grupo) >= max_palabras
                or palabra.fin - grupo[0].inicio > max_duracion
                or pausa >= corte_por_pausa
                or grupo[-1].texto[-1] in ".!?"
            ):
                cerrar()
        grupo.append(palabra)
    cerrar()
    return bloques


def a_srt(bloques: list[Bloque]) -> str:
    partes = []
    for numero, bloque in enumerate(bloques, start=1):
        partes.append(
            f"{numero}\n"
            f"{formatear_tiempo(bloque.inicio)} --> {formatear_tiempo(bloque.fin)}\n"
            f"{bloque.texto}\n"
        )
    return "\n".join(partes)


ESTILO_ASS = (
    "Style: Base,{fuente},{tamano},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
    "-1,0,0,0,100,100,0,0,1,{borde},{sombra},2,80,80,{margen},1"
)


def a_ass(
    bloques: list[Bloque],
    ancho: int = 1080,
    alto: int = 1920,
    fuente: str = "DejaVu Sans",
    mayusculas: bool = True,
) -> str:
    """Subtítulos quemables con ffmpeg: grandes, centrados, con borde negro."""
    tamano = round(alto * 0.045)          # ~86 px en vertical
    margen = round(alto * 0.17)           # sube el texto sobre el borde inferior
    cabecera = "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {ancho}",
        f"PlayResY: {alto}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,"
        " Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline,"
        " Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        ESTILO_ASS.format(
            fuente=fuente, tamano=tamano, borde=round(tamano * 0.09), sombra=round(tamano * 0.04),
            margen=margen,
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])

    lineas = []
    for bloque in bloques:
        texto = bloque.texto.upper() if mayusculas else bloque.texto
        texto = texto.replace("\n", r"\N").replace("{", "(").replace("}", ")")
        lineas.append(
            f"Dialogue: 0,{formatear_tiempo(bloque.inicio, '.')},{formatear_tiempo(bloque.fin, '.')},"
            f"Base,,0,0,0,,{texto}"
        )
    return cabecera + "\n" + "\n".join(lineas) + "\n"


def escribir(bloques: list[Bloque], destino_srt: Path, destino_ass: Path, ancho: int, alto: int) -> None:
    destino_srt.write_text(a_srt(bloques), encoding="utf-8")
    destino_ass.write_text(a_ass(bloques, ancho, alto), encoding="utf-8")
