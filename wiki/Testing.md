# Testing

The suite is **60 pytest tests** covering unit behaviour, the Django views, and an end-to-end flow. It is **fully offline** — all network and LLM calls are mocked — so it runs in ~0.5s and is safe for CI.

## Running

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Config: `pytest.ini` sets `testpaths = tests` and quiet output. The same command runs in the GitHub Actions `test` job.

## How things are mocked

- **HTTP**: tests monkeypatch the shared `app.http.SESSION.get` (and `requests` in the Ollama client) with a `FakeResponse` from `conftest.py` — no real OpenAlex/PDF/Ollama traffic.
- **PDFs**: `conftest.make_pdf_bytes()` builds a tiny real PDF with PyMuPDF so extraction is exercised for real.
- **OpenAlex works**: `conftest.make_work()` returns a representative work dict.
- **Anthropic**: a `FakeClient` stands in for the theme tagger.
- **Django views**: called directly via `RequestFactory`; `app.server`'s imported functions are monkeypatched (e.g. `fetch_metadata`, `download_many`, `chat`, `pick_model`).

## Shared fixtures (`tests/conftest.py`)

- `pdf_bytes` — valid PDF bytes with extractable text.
- `paper` — a populated `Paper`.
- `FakeResponse` — supports `.json()`, `.iter_content()`, `.raise_for_status()`, `.headers`.
- `make_work(**over)` — build an OpenAlex work dict (repository + publisher PDF locations, inverted-index abstract, topic, authorships with countries).

## What each file covers

| File | Focus |
|---|---|
| `test_config.py` | All config sections present; env overrides (`WORKERS`, `PORT`, `HOST`, `OPEN_BROWSER`, `OUTPUT_BASENAME`, `MAX_PAPERS_CAP`); load without env |
| `test_openalex.py` | `reconstruct_abstract` ordering/empty; `parse_work` fields, **repository-preferred** PDF ranking, de-dup, no-PDF; `fetch_metadata` yields, respects `n`, skips PDF-less papers, empty results |
| `test_download.py` | `_fetch_pdf_bytes` valid / rejects HTML / byte cap / deadline; `download_fulltext` success, candidate fallback, all-fail, no-candidates, exception handling; `download_many` parallelism + progress callback, empty list, worker-error survival |
| `test_corpus.py` | `build_corpus` metadata-only vs. with full text, column selection; `save_corpus` writes files and **creates missing parent dirs** |
| `test_theme.py` | `tag_theme` sets the theme, uses the abstract in the prompt, skips when empty |
| `test_ollama_client.py` | `list_models` (+ error path), `pick_model` (config / first-installed / none), `chat` request shape + answer |
| `test_retrieval.py` | `build_context` ranks relevant papers first, returns source metadata, respects the budget, falls back to abstract, and **survives `NaN` + numpy-array** columns from reloaded Parquet |
| `test_server.py` | `index` render + no-model banner; `build` validation, job start, no-results, **clamp to `max_papers_cap`**; `status` known/unknown; `ask` no-corpus / no-model / success / Ollama error |
| `test_e2e.py` | Full **build → ask** flow with mocked network + Ollama; the `pipeline` shim exposes the public API |

## Adding tests

- Put new tests in `tests/test_*.py`; reuse `conftest` fixtures.
- Keep them offline — monkeypatch `SESSION.get` / `requests` / `app.server` functions rather than hitting the network.
- For view tests, use `RequestFactory` and clear `server.JOBS` / `server.CORPUS` between tests (see the `clear_state` fixture pattern in `test_server.py`).

## Continuous integration

`.github/workflows/ci.yml` runs two jobs on every push/PR to `master`:
1. **test** — Python 3.11, install deps, `pytest`.
2. **docker** — `docker build` to validate the image.

See [Deployment](Deployment#continuous-integration) for details.
