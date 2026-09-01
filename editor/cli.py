"""Línea de comandos: python -m editor …"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import marcas, musica as musicas, voz as voces
from .config import Ajustes, FORMATOS, MUSICA
from .pipeline import crear_video


def _parser() -> argparse.ArgumentParser:
    principal = argparse.ArgumentParser(
        prog="editor", description="Editor automático de videos cortos."
    )
    comandos = principal.add_subparsers(dest="comando", required=True)

    comandos.add_parser("marcas", help="lista las marcas y cuántos clips tienen")
    comandos.add_parser("voces", help="lista las voces de tu cuenta de ElevenLabs")
    comandos.add_parser("musica", help="lista las pistas de assets/musica/")

    nueva = comandos.add_parser("marca-nueva", help="crea las carpetas de una marca")
    nueva.add_argument("nombre")

    servidor = comandos.add_parser("servidor", help="abre la interfaz web para subir clips")
    servidor.add_argument("--puerto", type=int, default=8000)
    servidor.add_argument("--host", default="127.0.0.1")

    video = comandos.add_parser("video", help="genera un video")
    video.add_argument("--marca", required=True)
    video.add_argument("--tema", help="de qué va el video (Claude escribe el guion)")
    video.add_argument("--guion", help="ruta a un guion ya escrito, o '-' para leerlo de la entrada")
    video.add_argument("--duracion", type=float, default=46.0, help="segundos (por defecto 46)")
    video.add_argument("--corte", type=float, default=2.0, help="segundos por corte (por defecto 2)")
    video.add_argument("--formato", choices=sorted(FORMATOS), default="vertical")
    video.add_argument("--voz", help="ID de voz de ElevenLabs")
    video.add_argument("--sin-voz", action="store_true", help="sin locución (subtítulos estimados)")
    video.add_argument("--musica", help="nombre de pista o de carpeta dentro de assets/musica")
    video.add_argument("--volumen-musica", type=float, default=0.14)
    video.add_argument("--audio-clips", type=float, default=0.0, help="volumen del audio original")
    video.add_argument("--sin-subtitulos", action="store_true")
    video.add_argument("--apoyos-cada", type=int, default=3,
                       help="cada cuántos cortes entra una toma de apoyo (0 para ninguna)")
    video.add_argument("--skill", help="ruta a un SKILL.md que dicte el estilo del guion")
    video.add_argument("--semilla", type=int, help="repite el mismo orden de cortes")
    video.add_argument("--conservar-temporales", action="store_true")
    return principal


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parser().parse_args(argv)

    if args.comando == "marcas":
        for marca in marcas.listar():
            print(f"{marca.nombre}: {len(marca.clips())} clip(s) por editar, "
                  f"{len(marca.clips_de_apoyo())} toma(s) de apoyo")
        return 0

    if args.comando == "marca-nueva":
        marca = marcas.obtener(args.nombre, crear=True)
        print(f"creada {marca.carpeta} (sube tus clips a {marca.por_editar})")
        return 0

    if args.comando == "voces":
        lista = voces.voces()
        if not lista:
            print("sin voces: falta ELEVENLABS_API_KEY en el .env")
            return 1
        for voz in lista:
            print(f"{voz['id']}  {voz['nombre']} {voz['idioma']}".rstrip())
        return 0

    if args.comando == "musica":
        pistas = musicas.pistas()
        if not pistas:
            print("no hay música todavía: mete mp3 en assets/musica/<ambiente>/")
            return 1
        for pista in pistas:
            print(pista.relative_to(MUSICA))
        return 0

    if args.comando == "servidor":
        from .servidor import arrancar

        arrancar(host=args.host, puerto=args.puerto)
        return 0

    texto_guion = None
    if args.guion:
        texto_guion = sys.stdin.read() if args.guion == "-" else Path(args.guion).read_text(encoding="utf-8")
    if not texto_guion and not args.tema:
        print("necesito --tema o --guion", file=sys.stderr)
        return 2

    ajustes = Ajustes(
        marca=args.marca,
        duracion_objetivo=args.duracion,
        duracion_corte=args.corte,
        formato=args.formato,
        voz_id=args.voz or "",
        musica=args.musica,
        volumen_musica=args.volumen_musica,
        volumen_clips=args.audio_clips,
        subtitulos=not args.sin_subtitulos,
        proporcion_tomas_apoyo=args.apoyos_cada,
        skill_guiones=args.skill,
        semilla=args.semilla,
    )
    resultado = crear_video(
        ajustes,
        tema=args.tema,
        texto_guion=texto_guion,
        sin_voz=args.sin_voz,
        avisar=print,
        conservar_temporales=args.conservar_temporales,
    )
    print(f"\nVideo: {resultado.video}")
    print(f"Copia en la marca: {resultado.copia_en_marca}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
