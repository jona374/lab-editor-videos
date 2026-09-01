"""Generación del guion con Claude (o carga de uno escrito a mano)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Ajustes, hay_clave_anthropic

REGLAS = """Escribes guiones para videos verticales cortos (Reels, TikTok, Shorts) en español neutro de Latinoamérica.

Reglas:
- El gancho son los primeros 3 segundos: una frase que frene el scroll. Nada de "hola, bienvenidos".
- Frases cortas, habladas, de una sola idea. Como habla una persona, no como escribe una marca.
- Nada de emojis, hashtags, acotaciones de cámara ni texto entre paréntesis: esto se lee en voz alta tal cual.
- Números y siglas escritos como se pronuncian (por ejemplo "veinticinco por ciento", no "25%").
- Cierra con un llamado a la acción concreto y fácil de decir.
- El largo manda: el guion completo debe durar lo que se pide al leerlo en voz alta a ritmo normal."""

ESQUEMA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string", "description": "Título interno del video, corto"},
        "gancho": {"type": "string", "description": "Primera frase, los 3 primeros segundos"},
        "cuerpo": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Frases del desarrollo, una idea por frase",
        },
        "cta": {"type": "string", "description": "Frase final de llamado a la acción"},
        "mood_musica": {
            "type": "string",
            "description": "Una palabra para el ambiente musical: energico, inspirador, calmado, urbano, elegante",
        },
        "tomas_de_apoyo": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tomas de apoyo sugeridas (b-roll), una descripción por toma",
        },
    },
    "required": ["titulo", "gancho", "cuerpo", "cta", "mood_musica", "tomas_de_apoyo"],
    "additionalProperties": False,
}


@dataclass
class Guion:
    titulo: str
    gancho: str
    cuerpo: list[str] = field(default_factory=list)
    cta: str = ""
    mood_musica: str = "energico"
    tomas_de_apoyo: list[str] = field(default_factory=list)

    def narracion(self) -> str:
        """El texto que se manda a ElevenLabs, tal cual se va a escuchar."""
        frases = [self.gancho, *self.cuerpo, self.cta]
        return " ".join(f.strip() for f in frases if f and f.strip())

    def palabras(self) -> int:
        return len(self.narracion().split())

    def a_markdown(self) -> str:
        lineas = [f"# {self.titulo}", "", f"**Gancho:** {self.gancho}", ""]
        lineas += [f"- {frase}" for frase in self.cuerpo]
        lineas += ["", f"**CTA:** {self.cta}", "", f"**Música:** {self.mood_musica}", ""]
        if self.tomas_de_apoyo:
            lineas += ["## Tomas de apoyo sugeridas", ""]
            lineas += [f"{i}. {t}" for i, t in enumerate(self.tomas_de_apoyo, 1)]
            lineas += [""]
        lineas += [f"_{self.palabras()} palabras_"]
        return "\n".join(lineas)


def desde_texto(texto: str, titulo: str = "Guion manual") -> Guion:
    """Guion escrito a mano: la primera frase es el gancho, la última el CTA."""
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+|\n+", texto.strip()) if f.strip()]
    if not frases:
        raise ValueError("el guion está vacío")
    if len(frases) == 1:
        return Guion(titulo=titulo, gancho=frases[0])
    return Guion(titulo=titulo, gancho=frases[0], cuerpo=frases[1:-1], cta=frases[-1])


def cargar(ruta: Path) -> Guion:
    return desde_texto(ruta.read_text(encoding="utf-8"), titulo=ruta.stem)


def _contexto(ajustes: Ajustes, prompt_marca: str) -> str:
    """Sistema = reglas + estilo de la marca + (opcional) una skill de guiones."""
    partes = [REGLAS]
    if prompt_marca.strip():
        partes.append(f"## Estilo de la marca «{ajustes.marca}»\n\n{prompt_marca.strip()}")
    if ajustes.skill_guiones:
        skill = Path(ajustes.skill_guiones)
        if not skill.exists():
            raise ValueError(f"no encuentro la skill de guiones: {skill}")
        partes.append(f"## Método de guionización a seguir\n\n{skill.read_text(encoding='utf-8')}")
    return "\n\n".join(partes)


def generar(tema: str, prompt_marca: str, ajustes: Ajustes) -> Guion:
    """Le pide el guion a Claude con salida estructurada (JSON garantizado)."""
    if not hay_clave_anthropic():
        raise RuntimeError(
            "falta ANTHROPIC_API_KEY para generar el guion. "
            "Escribe el guion a mano y pásalo con --guion, o pon la clave en el .env"
        )
    try:
        import anthropic
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise RuntimeError("falta el paquete 'anthropic' (pip install -r requirements.txt)") from error

    cliente = anthropic.Anthropic()
    peticion = (
        f"Escribe el guion de un video de {ajustes.duracion_objetivo:.0f} segundos "
        f"(unas {ajustes.palabras_objetivo} palabras en total, contando gancho y CTA).\n\n"
        f"Tema: {tema}"
    )
    respuesta = cliente.beta.messages.create(
        model=ajustes.modelo_claude,
        max_tokens=16000,
        system=_contexto(ajustes, prompt_marca),
        messages=[{"role": "user", "content": peticion}],
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": ESQUEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    texto = next((b.text for b in respuesta.content if b.type == "text"), None)
    if not texto:
        motivo = getattr(respuesta, "stop_details", None) or respuesta.stop_reason
        raise RuntimeError(f"Claude no devolvió guion (stop_reason={respuesta.stop_reason}, {motivo})")
    return Guion(**json.loads(texto))
