"""Orquestador: de los clips crudos al video publicable."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import guion as guiones
from . import marcas, musica as musicas, render, voz as voces
from .config import Ajustes
from .corte import Clip, Segmento, plan_de_corte, resumen
from .guion import Guion
from .subtitulos import Palabra, agrupar, escribir as escribir_subtitulos, estimar_palabras
from .utilidades import duracion as duracion_de, slug

log = logging.getLogger("editor")


@dataclass
class Resultado:
    video: Path
    copia_en_marca: Path | None
    carpeta: Path
    guion: Guion
    duracion: float
    segmentos: list[Segmento]
    musica: Path | None
    voz: Path | None
    subtitulos: Path | None

    def resumen(self) -> str:
        return (
            f"{self.video.name} — {self.duracion:.1f}s, {resumen(self.segmentos)}"
            f"{', con voz' if self.voz else ', sin voz'}"
            f"{f', música {self.musica.name}' if self.musica else ''}"
        )


def crear_video(
    ajustes: Ajustes,
    tema: str | None = None,
    texto_guion: str | None = None,
    sin_voz: bool = False,
    avisar=log.info,
    conservar_temporales: bool = False,
) -> Resultado:
    """Hace el video completo. `tema` lo escribe Claude; `texto_guion` lo pones tú."""
    marca = marcas.obtener(ajustes.marca)

    avisar(f"Marca «{marca.nombre}» — buscando clips…")
    clips = _leer_clips(marca.clips())
    apoyos = _leer_clips(marca.clips_de_apoyo(), apoyo=True)
    if not clips:
        raise ValueError(
            f"no hay clips en {marca.por_editar}. Sube ahí los videos crudos y vuelve a intentar."
        )
    avisar(f"{len(clips)} clip(s), {sum(c.duracion for c in clips):.0f}s de material"
           + (f" + {len(apoyos)} toma(s) de apoyo" if apoyos else ""))

    # 1. Guion
    if texto_guion and texto_guion.strip():
        guion = guiones.desde_texto(texto_guion, titulo=tema or "Guion manual")
        avisar(f"Guion recibido: {guion.palabras()} palabras")
    elif tema:
        avisar("Escribiendo el guion con Claude…")
        guion = guiones.generar(tema, marca.texto_prompt(), ajustes)
        avisar(f"Guion listo: «{guion.titulo}» ({guion.palabras()} palabras)")
    else:
        raise ValueError("dime un tema (para que Claude escriba el guion) o pásame el guion escrito")

    carpeta = marca.salidas / f"{datetime.now():%Y%m%d-%H%M}-{slug(guion.titulo)}"
    temporal = carpeta / "_temporal"
    temporal.mkdir(parents=True, exist_ok=True)
    (carpeta / "guion.md").write_text(guion.a_markdown(), encoding="utf-8")

    # 2. Voz
    locucion = None
    if not sin_voz:
        avisar("Generando la voz en ElevenLabs…")
        locucion = voces.generar(guion.narracion(), carpeta / "voz.mp3", ajustes)
        avisar(f"Voz lista: {locucion.duracion:.1f}s")

    # 3. Cuánto dura el video: lo pedido, o lo que dure la voz más un respiro
    duracion_final = ajustes.duracion_objetivo
    if locucion:
        duracion_final = max(duracion_final, locucion.duracion + ajustes.cola_silencio)
    if locucion and locucion.duracion > ajustes.duracion_objetivo + 3:
        avisar(
            f"Ojo: la voz dura {locucion.duracion:.1f}s y pediste {ajustes.duracion_objetivo:.0f}s. "
            "El video se alarga para que no se corte; acorta el guion si quieres clavar la duración."
        )

    # 4. Plan de corte
    segmentos = plan_de_corte(
        clips,
        duracion_total=duracion_final,
        duracion_corte=ajustes.duracion_corte,
        apoyos=apoyos,
        proporcion_apoyos=ajustes.proporcion_tomas_apoyo,
        semilla=ajustes.semilla,
    )
    avisar(f"Plan de corte: {resumen(segmentos)}")
    _guardar_plan(carpeta / "plan.json", ajustes, guion, segmentos, duracion_final)

    # 5. Subtítulos
    ruta_srt = ruta_ass = None
    if ajustes.subtitulos:
        palabras = _palabras(locucion, guion, duracion_final)
        if palabras:
            bloques = agrupar(
                palabras,
                max_caracteres=ajustes.max_caracteres_bloque,
                max_palabras=ajustes.max_palabras_bloque,
            )
            ruta_srt, ruta_ass = carpeta / "subtitulos.srt", temporal / "subtitulos.ass"
            ancho, alto = ajustes.resolucion
            escribir_subtitulos(bloques, ruta_srt, ruta_ass, ancho, alto)
            avisar(f"{len(bloques)} bloques de subtítulos")

    # 6. Música
    pista = musicas.elegir(ajustes.musica, guion.mood_musica, semilla=ajustes.semilla)
    if pista:
        avisar(f"Música: {pista.name}")
    elif ajustes.volumen_musica > 0:
        avisar("Sin música: no hay pistas en assets/musica/ (el video sale solo con la voz)")

    # 7. Render
    avisar(f"Cortando {len(segmentos)} trozos…")
    partes = render.recortar_segmentos(segmentos, temporal, ajustes)
    avisar("Uniendo los cortes…")
    mudo = render.concatenar(partes, temporal / "montaje.mp4")
    avisar("Montaje final (voz, música y subtítulos)…")
    video = render.montar(
        mudo, carpeta / f"{slug(guion.titulo)}.mp4", ajustes, duracion_final,
        voz=locucion.ruta if locucion else None, musica=pista, subtitulos_ass=ruta_ass,
    )

    if guion.tomas_de_apoyo:
        (carpeta / "tomas-de-apoyo.md").write_text(
            "# Tomas de apoyo sugeridas por el guion\n\n"
            + "\n".join(f"{i}. {t}" for i, t in enumerate(guion.tomas_de_apoyo, 1))
            + f"\n\nGrábalas o genéralas y déjalas en `{marca.tomas_de_apoyo}` "
              "para que entren solas en el próximo render.\n",
            encoding="utf-8",
        )

    copia = marca.listos / video.name
    marca.listos.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video, copia)

    if not conservar_temporales:
        shutil.rmtree(temporal, ignore_errors=True)

    resultado = Resultado(
        video=video, copia_en_marca=copia, carpeta=carpeta, guion=guion,
        duracion=duracion_de(video), segmentos=segmentos, musica=pista,
        voz=locucion.ruta if locucion else None, subtitulos=ruta_srt,
    )
    avisar("Listo: " + resultado.resumen())
    return resultado


def _leer_clips(rutas: list[Path], apoyo: bool = False) -> list[Clip]:
    clips = []
    for ruta in rutas:
        try:
            clips.append(Clip(ruta, duracion_de(ruta), apoyo=apoyo))
        except Exception as error:  # un clip corrupto no debe tumbar el render entero
            log.warning("me salto %s: %s", ruta.name, error)
    return clips


def _palabras(locucion, guion: Guion, duracion_final: float) -> list[Palabra]:
    """Tiempos reales si hubo voz; si no, un reparto estimado sobre la duración."""
    if locucion and locucion.palabras:
        return locucion.palabras
    return estimar_palabras(guion.narracion(), duracion_final)


def _guardar_plan(ruta: Path, ajustes: Ajustes, guion: Guion, segmentos: list[Segmento],
                  duracion_final: float) -> None:
    ruta.write_text(
        json.dumps(
            {
                "ajustes": ajustes.como_dict(),
                "duracion_final": round(duracion_final, 3),
                "guion": guion.__dict__,
                "cortes": [
                    {
                        "clip": s.ruta.name,
                        "inicio": round(s.inicio, 3),
                        "duracion": round(s.duracion, 3),
                        "apoyo": s.apoyo,
                    }
                    for s in segmentos
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
