# lab-editor-videos

**Banco de pruebas. Este NO es el repo bueno.**

El repo de producción es [`editor-de-videos`](https://github.com/jona374/editor-de-videos).
Aquí se prueban cosas antes de llevarlas allá.

## Qué se está probando ahora

Las **agent-skills** de Addy Osmani (copia en
[`jona374/agent-skills`](https://github.com/jona374/agent-skills)) aplicadas
al proyecto del editor de videos.

Están instaladas en `.claude/`:

- `.claude/skills/` — 25 skills del ciclo de desarrollo
- `.claude/commands/` — comandos slash (`/spec`, `/build`, `/test`, `/review`,
  `/ship`, `/code-simplify`, `/webperf`, `/planning`, `/constraints`)
- `.claude/agents/` — personas de revisión (revisor de código, ingeniero de
  pruebas, auditor de seguridad, auditor de rendimiento)

## Cómo usarlas

Abriendo este repo con Claude Code, las skills se activan solas según el
contexto, o se llaman a mano con los comandos slash:

| Comando | Para qué sirve |
|---|---|
| `/spec` | Definir qué se va a construir antes de escribir código |
| `/planning` | Partir el trabajo en tareas |
| `/build` | Implementar por partes, no todo de golpe |
| `/test` | Probar que funciona de verdad |
| `/review` | Revisar antes de dar por bueno |
| `/code-simplify` | Simplificar código enredado |
| `/ship` | Checklist antes de publicar |

## Estructura heredada del editor de videos

Se mantiene la misma organización por marca (ver `INSTRUCCIONES.md`):
cada marca tiene `videos-por-editar/`, `videos-listos/` y su `prompt.md`.

## Nota de licencia

Las skills en `.claude/` vienen de `addyosmani/agent-skills` y conservan su
licencia original (ver `LICENSE`).
