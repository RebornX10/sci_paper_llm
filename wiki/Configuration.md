# Configuration

All tunable settings live in **`config.yaml`** at the repo root. Every value can be overridden at runtime with an environment variable, which is how the Docker/Compose/Codespaces/HF deployments adjust behaviour without editing files.

Config is loaded once by [`app/config.py`](Code-Reference#appconfigpy) into the `CONFIG` dict.

## `config.yaml` reference

```yaml
server:
  host: 127.0.0.1        # bind address (use 0.0.0.0 in containers)
  port: 8000             # web server port
  open_browser: true     # auto-open a browser tab on start

openalex:
  mailto: you@example.com           # your email -> OpenAlex "polite pool" (faster)
  per_page: 200                     # OpenAlex page size (max 200)
  default_search: null              # default free-text query (null = all fields)
  default_filters: "from_publication_date:2022-01-01"  # default OpenAlex filter
  max_papers: 25                    # default "Max papers" value in the UI
  max_papers_cap: 10000             # hard upper limit a request may ask for

download:
  workers: 14            # parallel PDF downloads
  paper_deadline_s: 45   # wall-clock budget per paper across all candidate URLs
  max_pdf_bytes: 30000000  # stop reading PDFs larger than this (~30 MB)
  connect_timeout: 5     # per-request connect timeout (s)
  read_timeout: 40       # per-request read timeout (s)
  max_chars: 400000      # truncate extracted text to this many characters
  output_basename: papers  # output path -> <basename>.parquet / .csv

ollama:
  url: http://localhost:11434  # Ollama endpoint
  model: null                  # null = auto-detect first installed model
  request_timeout: 300         # seconds to wait for an answer

retrieval:
  top_k: 5             # how many papers to feed the model per question
  context_budget: 9000 # max characters of context sent to the model

theme:
  anthropic_model: claude-opus-4-8  # model used only if with_theme=True (needs ANTHROPIC_API_KEY)
```

## Environment-variable overrides

These are applied on top of `config.yaml` by `app/config.py`:

| Env var | Overrides | Type |
|---|---|---|
| `HOST` | `server.host` | str |
| `PORT` | `server.port` | int |
| `OPEN_BROWSER` | `server.open_browser` | bool (`1/true/yes/on`) |
| `OPENALEX_MAILTO` | `openalex.mailto` | str |
| `MAX_PAPERS_CAP` | `openalex.max_papers_cap` | int |
| `WORKERS` | `download.workers` | int |
| `OUTPUT_BASENAME` | `download.output_basename` | str |
| `OLLAMA_URL` | `ollama.url` | str |
| `OLLAMA_MODEL` | `ollama.model` | str |

Example:

```bash
PORT=9000 WORKERS=16 OLLAMA_MODEL=llama3.2:1b ./run.sh
```

A custom config file path can be set with `CONFIG_FILE=/path/to/config.yaml`.

## Tuning notes

- **Speed vs. coverage:** lowering `download.paper_deadline_s` makes builds faster but drops slow-but-valid PDFs (less full-text coverage). More `workers` helps until you hit the per-paper deadline "straggler floor".
- **Memory:** the whole corpus (full text included) is held in RAM during a build. `max_chars` caps per-paper text; `max_papers_cap` caps the count. Keep these sane for the machine you run on (especially small free Spaces).
- **LLM theme tags:** by default `theme` comes free from OpenAlex topics. Set `ANTHROPIC_API_KEY` and call with `with_theme=True` to generate custom tags with Claude instead.
- **Anthropic API & prompt caching:** if you extend the theme tagger or add other Claude calls, see the Claude API skill for prompt-caching guidance.
