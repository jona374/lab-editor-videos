"""Voz en off con ElevenLabs, con los tiempos de cada palabra para los subtítulos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Ajustes, clave_elevenlabs
from .subtitulos import Palabra, palabras_desde_alineacion
from .utilidades import duracion as duracion_de

API = "https://api.elevenlabs.io/v1"
TIEMPO_LIMITE = 180  # segundos: el TTS de un guion largo puede tardar


@dataclass
class Locucion:
    ruta: Path
    duracion: float
    palabras: list[Palabra]


class ErrorElevenLabs(RuntimeError):
    pass


def _cliente():
    try:
        import requests
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise RuntimeError("falta el paquete 'requests' (pip install -r requirements.txt)") from error
    return requests


def voces() -> list[dict]:
    """Las voces de la cuenta: [{'id':..., 'nombre':..., 'idioma':...}]."""
    clave = clave_elevenlabs()
    if not clave:
        return []
    requests = _cliente()
    respuesta = requests.get(f"{API}/voices", headers={"xi-api-key": clave}, timeout=30)
    _revisar(respuesta)
    return [
        {
            "id": v["voice_id"],
            "nombre": v.get("name", ""),
            "idioma": (v.get("labels") or {}).get("language", ""),
        }
        for v in respuesta.json().get("voices", [])
    ]


def generar(texto: str, destino: Path, ajustes: Ajustes) -> Locucion:
    """Convierte el guion en un mp3 y devuelve la alineación palabra por palabra."""
    clave = clave_elevenlabs()
    if not clave:
        raise ErrorElevenLabs(
            "falta ELEVENLABS_API_KEY. Ponla en el .env o genera el video sin voz (--sin-voz)."
        )
    if not ajustes.voz_id:
        raise ErrorElevenLabs(
            "falta la voz: pon ELEVENLABS_VOICE_ID en el .env o pásala con --voz."
        )
    if not texto.strip():
        raise ErrorElevenLabs("el guion está vacío, no hay nada que locutar")

    requests = _cliente()
    respuesta = requests.post(
        f"{API}/text-to-speech/{ajustes.voz_id}/with-timestamps",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": clave, "Content-Type": "application/json"},
        json={
            "text": texto,
            "model_id": ajustes.modelo_voz,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.8,
                "style": 0.15,
                "use_speaker_boost": True,
                "speed": ajustes.velocidad_voz,
            },
        },
        timeout=TIEMPO_LIMITE,
    )
    _revisar(respuesta)
    datos = respuesta.json()

    import base64

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(base64.b64decode(datos["audio_base64"]))

    alineacion = datos.get("alignment") or datos.get("normalized_alignment") or {}
    palabras = palabras_desde_alineacion(
        alineacion.get("characters", []),
        alineacion.get("character_start_times_seconds", []),
        alineacion.get("character_end_times_seconds", []),
    )
    return Locucion(destino, duracion_de(destino), palabras)


def _revisar(respuesta) -> None:
    if respuesta.status_code >= 400:
        detalle = respuesta.text[:400]
        if respuesta.status_code == 401:
            detalle = "la ELEVENLABS_API_KEY no es válida"
        elif respuesta.status_code == 422:
            detalle = f"ElevenLabs rechazó la petición (¿voz o modelo mal?): {detalle}"
        raise ErrorElevenLabs(f"ElevenLabs devolvió {respuesta.status_code}: {detalle}")
