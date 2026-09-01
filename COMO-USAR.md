# Editor automático de videos — cómo se usa

Subes clips crudos, dices de qué va el video, y la app devuelve un video vertical
con voz en off, cortes cada 2 segundos, subtítulos quemados y música de fondo.

## Opción rápida: sin instalar nada (Google Colab)

Si tu computadora es vieja o no puedes instalar programas, corre todo en el navegador,
gratis, en los servidores de Google:

**[▶ Abrir el editor en Colab](https://colab.research.google.com/github/jona374/lab-editor-videos/blob/claude/auto-video-editing-app-rft92m/colab/editor_en_colab.ipynb)**

Subes los clips con un botón, llenas el tema y descargas el video. Necesitas una cuenta
de Google y nada más. El cuaderno está en `colab/editor_en_colab.ipynb`.

Ojo: Colab se apaga solo tras un rato sin usarlo y borra los archivos subidos; para
trabajo diario conviene instalarlo en una computadora (abajo).

## 1. Instalar en tu computadora (una sola vez)

```bash
./instalar.sh          # crea el entorno, instala todo y revisa que exista ffmpeg
cp .env.example .env   # y rellena las dos claves
```

En el `.env`:

| Clave | Para qué | Dónde se saca |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude escribe el guion | console.anthropic.com |
| `ELEVENLABS_API_KEY` | La voz en off | elevenlabs.io → Profile → API key |
| `ELEVENLABS_VOICE_ID` | Qué voz usa por defecto | `python -m editor voces` las lista |

Sin claves la app igual funciona: pásale el guion escrito a mano y usa `--sin-voz`
para sacar el borrador mudo (con subtítulos estimados) sin gastar créditos.

## 2. Poner el material

```
<marca>/
  videos-por-editar/   ← los clips crudos (de aquí sale el video)
  tomas-de-apoyo/      ← b-roll: entra 1 de cada 3 cortes
  videos-listos/       ← aquí se copia el video terminado
  prompt.md            ← estilo de la marca: tono, a quién le habla, CTA
assets/musica/
  energico/  calmado/  ← mp3 por ambiente; el guion elige el que pega
```

El `prompt.md` de la marca se le pasa a Claude tal cual cuando escribe el guion:
mientras mejor esté escrito, más se parece el guion a tu marca.

## 3. Hacer un video

**Con la interfaz web** (lo más cómodo: se arrastran los clips y se ve el resultado):

```bash
.venv/bin/python -m editor servidor      # abre http://127.0.0.1:8000
```

**Desde la terminal:**

```bash
# Claude escribe el guion a partir del tema
.venv/bin/python -m editor video --marca textiles-pelileo \
  --tema "por qué el pantalón cargo aguanta el trabajo pesado"

# Tu guion, video de un minuto, cortes cada 1.5 s
.venv/bin/python -m editor video --marca textiles-pelileo \
  --guion guion.txt --duracion 60 --corte 1.5

# Borrador rápido, sin gastar ElevenLabs
.venv/bin/python -m editor video --marca textiles-pelileo --tema "..." --sin-voz
```

Otros comandos: `marcas`, `marca-nueva <nombre>`, `voces`, `musica`.

## 4. Qué queda al terminar

En `salidas/<marca>/<fecha>-<titulo>/`:

| Archivo | Qué es |
|---|---|
| `<titulo>.mp4` | el video (copiado también a `<marca>/videos-listos/`) |
| `guion.md` | el guion que se locutó |
| `voz.mp3` | la locución suelta |
| `subtitulos.srt` | por si quieres subirlos aparte en vez de quemados |
| `plan.json` | qué trozo de qué clip fue a cada corte, y con qué ajustes |
| `tomas-de-apoyo.md` | el b-roll que sugirió el guion, para grabarlo o generarlo |

## Cómo trabaja por dentro

1. **Guion** — Claude (`claude-opus-5`) escribe gancho, cuerpo y CTA con el largo
   justo para la duración pedida (~2.75 palabras por segundo), siguiendo el
   `prompt.md` de la marca. Con `--skill ruta/SKILL.md` le impones además tu propio
   método de guionización.
2. **Voz** — ElevenLabs devuelve el audio *y* el tiempo exacto de cada letra, así que
   los subtítulos calzan con la voz sin transcribir nada.
3. **Corte** — se reparte la duración en trozos de 2 s alternando clips, sin repetir
   el mismo trozo y reutilizando material si no alcanza.
4. **Subtítulos** — bloques de 3-4 palabras, en mayúsculas, con borde negro, quemados.
5. **Música** — se elige por el ambiente del guion y se agacha sola cuando habla la
   voz (ducking).

La duración manda: si la voz sale más larga que los 46 s pedidos, el video se
alarga para no cortarla y te avisa en pantalla.

## Ajustes que se tocan seguido

Están en `editor/config.py` (`Ajustes`), y casi todos tienen bandera en la terminal:
duración, segundos por corte, formato (`vertical`, `cuadrado`, `horizontal`),
volumen de música, volumen del audio original de los clips, tamaño de los bloques
de subtítulo y cada cuántos cortes entra una toma de apoyo.

`--semilla 7` repite exactamente el mismo orden de cortes: sirve para cambiar solo
el guion o la música y comparar peras con peras.

## Qué falta todavía (siguiente iteración)

- Generar las tomas de apoyo con IA (hoy solo se sugieren en `tomas-de-apoyo.md`).
- Elegir el trozo de cada clip por lo que se ve, no por turno (detectar movimiento,
  caras o el producto).
- Cuadrar los cortes con el ritmo de la música.
- Texto en pantalla del gancho los primeros 3 segundos.
