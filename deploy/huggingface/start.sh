#!/usr/bin/env bash
# sci_paper_llm — Samuel Adone (GitHub: RebornX10) — MIT
set -e

ollama serve &
until curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; do sleep 1; done
ollama pull "${OLLAMA_MODEL}"

cd /home/user/app
exec python main.py
