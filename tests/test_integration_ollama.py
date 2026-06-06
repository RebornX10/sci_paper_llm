"""Live Ollama integration tests — skipped unless RUN_OLLAMA_INTEGRATION is set
(and a real Ollama server with a model is reachable). The CI 'ollama-integration'
workflow sets it; the normal suite skips these."""
import os

import pandas as pd
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_OLLAMA_INTEGRATION"),
    reason="set RUN_OLLAMA_INTEGRATION=1 with a running Ollama to enable",
)


def test_chat_against_real_ollama():
    from app.ollama_client import chat, pick_model
    model = pick_model()
    assert model, "no Ollama model installed"
    answer = chat("What city is named?",
                  "[1] Title: Geo\nExcerpt: The capital of France is Paris.", model)
    assert isinstance(answer, str) and answer.strip()


def test_build_context_then_chat():
    from app.ollama_client import chat, pick_model
    from app.retrieval import build_context
    df = pd.DataFrame([{"title": "Paris", "abstract": "capital",
                        "content": "Paris is the capital of France.",
                        "authors": ["A"], "journal": "J", "date": "2023"}])
    ctx, sources = build_context(df, "capital of France")
    assert sources
    answer = chat("capital of France?", ctx, pick_model())
    assert answer.strip()
