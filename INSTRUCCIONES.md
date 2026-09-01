# Instrucciones internas — Editor de Videos

Este repositorio organiza los videos por marca/negocio de Jonathan.

## Regla fija
Cada vez que se agregue una marca o negocio nuevo, se debe crear una
carpeta con su nombre y, dentro de ella, siempre esto:

- `videos-por-editar/`  → videos crudos que aún no se han editado
- `videos-listos/`      → videos ya editados, listos para publicar
- `tomas-de-apoyo/`     → b-roll de esa marca (entra solo en los cortes)
- `prompt.md`           → instrucciones específicas de edición/estilo
                           para esa marca (tono, colores, música, CTA, etc.)

Las carpetas se crean solas con `python -m editor marca-nueva <nombre>`.

## Marcas actuales
- `textiles-pelileo/` (la primera, ya creada)

## Flujo de trabajo
1. Jonathan sube los clips crudos a `<marca>/videos-por-editar/`
2. Pide el video: por la interfaz web o con
   `python -m editor video --marca <marca> --tema "..."`
3. La app escribe el guion con el `prompt.md` de la marca, genera la voz,
   corta, subtitula y mezcla la música
4. El video terminado queda en `<marca>/videos-listos/` y todo lo demás
   (guion, voz, subtítulos, plan del corte) en `salidas/<marca>/`

Ver [COMO-USAR.md](COMO-USAR.md) para el detalle.
