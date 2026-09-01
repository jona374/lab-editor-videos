"""Plan de corte: qué trozo de qué clip va en cada hueco de 2 segundos.

Es lógica pura (no toca ffmpeg) para poder probarla sin renderizar nada.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Clip:
    ruta: Path
    duracion: float
    apoyo: bool = False  # True si viene de tomas-de-apoyo/


@dataclass(frozen=True)
class Segmento:
    """Un corte del video final: 'de este clip, desde el segundo X, Y segundos'."""

    ruta: Path
    inicio: float
    duracion: float
    apoyo: bool = False

    @property
    def fin(self) -> float:
        return self.inicio + self.duracion


class _Cursor:
    """Recorre un clip en ventanas, y vuelve al principio cuando se acaba."""

    def __init__(self, clip: Clip, arranque: float = 0.0):
        self.clip = clip
        self.posicion = arranque
        self.vueltas = 0

    def siguiente(self, pedido: float) -> tuple[float, float] | None:
        """Devuelve (inicio, duracion) o None si el clip es más corto que el pedido."""
        util = self.clip.duracion
        if util < pedido:
            return None
        if self.posicion + pedido > util:  # se acabó: rebobina
            self.posicion = 0.0
            self.vueltas += 1
        inicio = self.posicion
        self.posicion += pedido
        return inicio, pedido


def plan_de_corte(
    clips: list[Clip],
    duracion_total: float,
    duracion_corte: float = 2.0,
    apoyos: list[Clip] | None = None,
    proporcion_apoyos: int = 3,
    semilla: int | None = None,
) -> list[Segmento]:
    """Reparte `duracion_total` en cortes de `duracion_corte`, alternando clips.

    - Va rotando entre los clips para que dos cortes seguidos no salgan del mismo.
    - Si el material no alcanza, reutiliza los clips desde el principio.
    - Cada `proporcion_apoyos` cortes mete una toma de apoyo, si hay.
    - El último corte se recorta para que el total cuadre exacto.
    """
    if not clips:
        raise ValueError("no hay clips para editar: sube videos a <marca>/videos-por-editar/")
    if duracion_total <= 0:
        raise ValueError("la duración total tiene que ser mayor que 0")

    azar = random.Random(semilla)
    principales = [_Cursor(c, arranque=0.0) for c in clips if c.duracion > 0]
    if not principales:
        raise ValueError("los clips no tienen duración legible")
    de_apoyo = [_Cursor(c) for c in (apoyos or []) if c.duracion > 0]

    # Arranca en un clip cualquiera (con semilla fija, siempre el mismo).
    orden = list(range(len(principales)))
    azar.shuffle(orden)

    segmentos: list[Segmento] = []
    acumulado = 0.0
    indice = 0
    while acumulado < duracion_total - 1e-6:
        restante = duracion_total - acumulado
        pedido = min(duracion_corte, restante)

        cursor = None
        toca_apoyo = de_apoyo and proporcion_apoyos > 0 and (len(segmentos) + 1) % proporcion_apoyos == 0
        if toca_apoyo:
            cursor = _elegir(de_apoyo, pedido, len(segmentos))
        if cursor is None:
            cursor = _elegir(principales, pedido, orden[indice % len(orden)])
            indice += 1
        if cursor is None:
            # Ningún clip llega a `pedido`: cae al corte más largo posible.
            cursor = max(principales + de_apoyo, key=lambda c: c.clip.duracion)
            pedido = min(pedido, cursor.clip.duracion)
            if pedido <= 0.05:
                raise ValueError("los clips son demasiado cortos para cortar")

        ventana = cursor.siguiente(pedido)
        if ventana is None:  # defensivo: no debería pasar tras el ajuste de arriba
            raise ValueError("no pude encajar un corte con el material disponible")
        inicio, largo = ventana
        segmentos.append(Segmento(cursor.clip.ruta, inicio, largo, cursor.clip.apoyo))
        acumulado += largo

    return segmentos


def _elegir(cursores: list[_Cursor], pedido: float, preferido: int) -> _Cursor | None:
    """El cursor preferido si su clip da la talla; si no, el siguiente que sí."""
    total = len(cursores)
    for salto in range(total):
        cursor = cursores[(preferido + salto) % total]
        if cursor.clip.duracion >= pedido:
            return cursor
    return None


def resumen(segmentos: list[Segmento]) -> str:
    total = sum(s.duracion for s in segmentos)
    apoyos = sum(1 for s in segmentos if s.apoyo)
    fuentes = len({s.ruta for s in segmentos})
    return (
        f"{len(segmentos)} cortes / {total:.1f}s / {fuentes} clip(s)"
        + (f" / {apoyos} toma(s) de apoyo" if apoyos else "")
    )
