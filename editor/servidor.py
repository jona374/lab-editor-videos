"""Interfaz web: subir clips, pedir el video y ver cómo va."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from . import marcas, musica as musicas, voz as voces
from .config import RAIZ, SALIDAS, Ajustes, FORMATOS, clave_elevenlabs, hay_clave_anthropic
from .pipeline import crear_video

log = logging.getLogger("editor")
WEB = RAIZ / "web"


@dataclass
class Trabajo:
    id: str
    estado: str = "en cola"  # en cola | trabajando | listo | error
    mensajes: list[str] = field(default_factory=list)
    video: str | None = None
    carpeta: str | None = None
    error: str | None = None


TRABAJOS: dict[str, Trabajo] = {}
CANDADO = threading.Lock()


class PeticionVideo(BaseModel):
    marca: str
    tema: str | None = None
    guion: str | None = None
    duracion: float = 46.0
    corte: float = 2.0
    formato: str = "vertical"
    voz_id: str | None = None
    sin_voz: bool = False
    musica: str | None = None
    subtitulos: bool = True
    semilla: int | None = None


app = FastAPI(title="Editor automático de videos")


@app.get("/", response_class=HTMLResponse)
def inicio() -> str:
    return (WEB / "index.html").read_text(encoding="utf-8")


@app.get("/api/estado")
def estado() -> dict:
    return {
        "marcas": [
            {
                "nombre": m.nombre,
                "clips": [c.name for c in m.clips()],
                "apoyos": [c.name for c in m.clips_de_apoyo()],
            }
            for m in marcas.listar()
        ],
        "musica": [str(p.relative_to(musicas.MUSICA)) for p in musicas.pistas()],
        "formatos": sorted(FORMATOS),
        "claves": {"anthropic": hay_clave_anthropic(), "elevenlabs": bool(clave_elevenlabs())},
    }


@app.get("/api/voces")
def listar_voces() -> list[dict]:
    try:
        return voces.voces()
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.post("/api/marcas/{nombre}")
def crear_marca(nombre: str) -> dict:
    marca = marcas.obtener(_seguro(nombre), crear=True)
    return {"nombre": marca.nombre, "carpeta": str(marca.carpeta)}


@app.post("/api/marcas/{nombre}/clips")
async def subir_clips(nombre: str, apoyo: bool = False, archivos: list[UploadFile] = File(...)) -> dict:
    marca = marcas.obtener(_seguro(nombre), crear=True)
    destino_base = marca.tomas_de_apoyo if apoyo else marca.por_editar
    destino_base.mkdir(parents=True, exist_ok=True)

    guardados = []
    for archivo in archivos:
        nombre_limpio = Path(archivo.filename or "clip.mp4").name
        destino = destino_base / nombre_limpio
        with destino.open("wb") as salida:
            while trozo := await archivo.read(1024 * 1024):
                salida.write(trozo)
        guardados.append(nombre_limpio)
    return {"guardados": guardados, "carpeta": str(destino_base)}


@app.post("/api/videos")
def pedir_video(peticion: PeticionVideo, tareas: BackgroundTasks) -> dict:
    if not peticion.tema and not peticion.guion:
        raise HTTPException(status_code=400, detail="dime un tema o pásame el guion escrito")
    trabajo = Trabajo(id=uuid.uuid4().hex[:8])
    with CANDADO:
        TRABAJOS[trabajo.id] = trabajo
    tareas.add_task(_trabajar, trabajo, peticion)
    return {"id": trabajo.id}


@app.get("/api/trabajos/{identificador}")
def ver_trabajo(identificador: str) -> Trabajo:
    trabajo = TRABAJOS.get(identificador)
    if not trabajo:
        raise HTTPException(status_code=404, detail="no existe ese trabajo")
    return trabajo


@app.get("/api/video")
def descargar(ruta: str) -> FileResponse:
    """Sirve un video ya renderizado (solo de dentro de salidas/)."""
    archivo = Path(ruta).resolve()
    if not archivo.is_file() or SALIDAS.resolve() not in archivo.parents:
        raise HTTPException(status_code=404, detail="no encuentro ese video")
    return FileResponse(archivo, media_type="video/mp4", filename=archivo.name)


def _trabajar(trabajo: Trabajo, peticion: PeticionVideo) -> None:
    def avisar(mensaje: str) -> None:
        log.info(mensaje)
        trabajo.mensajes.append(str(mensaje))

    trabajo.estado = "trabajando"
    try:
        ajustes = Ajustes(
            marca=_seguro(peticion.marca),
            duracion_objetivo=peticion.duracion,
            duracion_corte=peticion.corte,
            formato=peticion.formato,
            voz_id=peticion.voz_id or "",
            musica=peticion.musica,
            subtitulos=peticion.subtitulos,
            semilla=peticion.semilla,
        )
        resultado = crear_video(
            ajustes, tema=peticion.tema, texto_guion=peticion.guion,
            sin_voz=peticion.sin_voz, avisar=avisar,
        )
        trabajo.video = str(resultado.video)
        trabajo.carpeta = str(resultado.carpeta)
        trabajo.estado = "listo"
    except Exception as error:
        log.exception("falló el render")
        trabajo.error = str(error)
        trabajo.estado = "error"


def _seguro(nombre: str) -> str:
    """Evita que un nombre de marca se salga de la carpeta del proyecto."""
    limpio = Path(nombre).name.strip()
    if not limpio or limpio.startswith("."):
        raise HTTPException(status_code=400, detail="nombre de marca inválido")
    return limpio


def arrancar(host: str = "127.0.0.1", puerto: int = 8000) -> None:  # pragma: no cover
    import uvicorn

    print(f"Abre http://{host}:{puerto} en el navegador (Ctrl+C para parar)")
    uvicorn.run(app, host=host, port=puerto, log_level="warning")
