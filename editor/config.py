"""Ajustes del editor. Todo lo que se puede tocar sin meterse en el código."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

try:  # opcional: si está instalado, lee el .env de la raíz
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover - el .env es una comodidad, no un requisito
    pass

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "salidas"
MUSICA = RAIZ / "assets" / "musica"

# Ancho x alto por formato de publicación.
FORMATOS = {
    "vertical": (1080, 1920),   # Reels, TikTok, Shorts
    "cuadrado": (1080, 1080),
    "horizontal": (1920, 1080),
}

# Palabras por segundo de una narración en español a ritmo de redes (~165 ppm).
PALABRAS_POR_SEGUNDO = 2.75


@dataclass
class Ajustes:
    """Parámetros de un render. Se crean por video, no son globales."""

    marca: str
    duracion_objetivo: float = 46.0
    duracion_corte: float = 2.0
    formato: str = "vertical"
    fps: int = 30

    # Guion
    modelo_claude: str = "claude-opus-5"
    skill_guiones: str | None = None  # ruta a un SKILL.md que dicta el estilo

    # Voz (ElevenLabs)
    voz_id: str = ""
    modelo_voz: str = "eleven_multilingual_v2"
    velocidad_voz: float = 1.0

    # Audio
    volumen_musica: float = 0.14      # 0 = sin música
    volumen_clips: float = 0.0        # 0 = clips mudos (manda la voz en off)
    cola_silencio: float = 0.6        # aire al final después de la última palabra

    # Subtítulos
    subtitulos: bool = True
    max_caracteres_bloque: int = 26
    max_palabras_bloque: int = 4

    # Tomas de apoyo: 1 de cada N cortes sale de <marca>/tomas-de-apoyo/
    proporcion_tomas_apoyo: int = 3

    musica: str | None = None         # nombre o carpeta de mood dentro de assets/musica
    semilla: int | None = None        # fija el orden de los cortes (para repetir un render)

    def __post_init__(self) -> None:
        if self.formato not in FORMATOS:
            raise ValueError(f"formato desconocido: {self.formato!r} (usa {', '.join(FORMATOS)})")
        if self.duracion_corte <= 0:
            raise ValueError("duracion_corte tiene que ser mayor que 0")
        if self.duracion_objetivo < self.duracion_corte:
            raise ValueError("duracion_objetivo tiene que ser mayor que duracion_corte")
        if not self.voz_id:
            self.voz_id = os.getenv("ELEVENLABS_VOICE_ID", "")

    @property
    def resolucion(self) -> tuple[int, int]:
        return FORMATOS[self.formato]

    @property
    def palabras_objetivo(self) -> int:
        """Cuántas palabras debe tener el guion para durar lo pedido."""
        return round(self.duracion_objetivo * PALABRAS_POR_SEGUNDO)

    def como_dict(self) -> dict:
        return asdict(self)


def clave_elevenlabs() -> str | None:
    return os.getenv("ELEVENLABS_API_KEY") or None


def hay_clave_anthropic() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
