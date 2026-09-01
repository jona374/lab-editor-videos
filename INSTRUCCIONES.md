# Instrucciones internas — Editor de Videos

Este repositorio organiza los videos por marca/negocio de Jonathan.

## Regla fija
Cada vez que se agregue una marca o negocio nuevo, se debe crear una
carpeta con su nombre y, dentro de ella, siempre estas tres cosas:

- `videos-por-editar/`  → videos crudos que aún no se han editado
- `videos-listos/`      → videos ya editados, listos para publicar
- `prompt.md`           → instrucciones específicas de edición/estilo
                           para esa marca (tono, colores, música, CTA, etc.)

## Marcas actuales
- `textiles-pelileo/` (la primera, ya creada)

## Flujo de trabajo
1. Jonathan sube un video crudo a `<marca>/videos-por-editar/`
2. Avisa en el chat qué video editar
3. Claude descarga el video, lo edita según `<marca>/prompt.md`
4. El resultado final se sube a `<marca>/videos-listos/`
