#!/usr/bin/env bash
# Deja el editor listo para usar: entorno, dependencias y revisión de ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v ffmpeg >/dev/null; then
  echo "Falta ffmpeg. Instálalo así:"
  echo "  Mac:    brew install ffmpeg"
  echo "  Ubuntu: sudo apt install ffmpeg"
  echo "  Windows: winget install Gyan.FFmpeg"
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

[ -f .env ] || { cp .env.example .env; echo "Creado .env — rellena tus claves."; }

echo "Listo. Prueba con:"
echo "  .venv/bin/python -m editor servidor"
