from __future__ import annotations

import io
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

import fitz

from app.config import CONFIG
from app.http import BROWSER_UA, SESSION
from app.models import Paper
from app.system import download_workers

log = logging.getLogger("download")

_DL = CONFIG["download"]
_CHUNK = 256 * 1024  # stream read size; larger = less per-PDF Python loop overhead

# Malformed PDFs make MuPDF spew "syntax error / object is not a stream" lines to
# the C stderr; silence them so they don't flood the logs (we handle failures in
# Python instead). Guarded for PyMuPDF versions without TOOLS.
try:
    fitz.TOOLS.mupdf_display_errors(False)
except Exception:
    pass


def _extract_text(data: bytes, max_chars: int, deadline: float) -> str:
    """Extract text page-by-page, tolerant of corrupt PDFs. A single bad page is
    skipped rather than aborting the whole document, parsing stops once we have
    enough text, and the per-paper `deadline` bounds total parse time so a
    pathological PDF can't hang a worker (which previously froze whole builds)."""
    parts, total = [], 0
    try:
        with fitz.open(stream=io.BytesIO(data), filetype="pdf") as doc:
            for page in doc:
                if time.monotonic() > deadline:
                    break
                try:
                    t = str(page.get_text())
                except Exception:
                    continue  # skip the corrupt page, keep the rest of the document
                if t:
                    parts.append(t)
                    total += len(t)
                    if total >= max_chars:
                        break  # we already have enough; don't parse the whole doc
    except Exception as e:
        log.warning("PDF parse error (skipping): %s", e)
    return "".join(parts)[:max_chars].strip()


def _fetch_pdf_bytes(url: str, deadline: float) -> Optional[bytes]:
    r = SESSION.get(
        url,
        timeout=(_DL["connect_timeout"], _DL["read_timeout"]),
        headers={"User-Agent": BROWSER_UA},
        stream=True,
    )
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").lower()
    buf, total = bytearray(), 0
    for chunk in r.iter_content(_CHUNK):
        buf += chunk
        total += len(chunk)
        if total == len(chunk) and "pdf" not in ctype and buf[:4] != b"%PDF":
            r.close()
            return None
        if total > _DL["max_pdf_bytes"] or time.monotonic() > deadline:
            r.close()
            break
    return bytes(buf)


def download_fulltext(
    paper: Paper,
    *,
    max_chars: int = _DL["max_chars"],
    deadline_s: float = _DL["paper_deadline_s"],
) -> Paper:
    candidates = paper.pdf_candidates or ([paper.pdf_url] if paper.pdf_url else [])
    deadline = time.monotonic() + deadline_s
    for url in candidates:
        if time.monotonic() > deadline:
            break
        try:
            log.info("GET pdf: %s", url)
            data = _fetch_pdf_bytes(url, deadline)
            if not data:
                continue
            text = _extract_text(data, max_chars, deadline)
            if text:
                paper.content = text
                paper.pdf_url = url
                log.info("  -> %d chars from %s", len(text), url)
                return paper
        except Exception as e:
            log.warning("download failed for %s: %s", url, e)
    return paper


def download_many(
    papers: list[Paper],
    *,
    workers: Optional[int] = None,
    progress: Optional[Callable[[int, int, Paper], None]] = None,
    stop: Optional[Callable[[int], bool]] = None,
) -> list[Paper]:
    total = len(papers)
    if total == 0:
        return papers
    if workers is None:
        workers = download_workers()
    workers = max(1, min(workers, total))
    log.info("Downloading %d papers with %d parallel workers", total, workers)
    done = 0
    ex = ThreadPoolExecutor(max_workers=workers)
    futures = {ex.submit(download_fulltext, p): p for p in papers}
    try:
        for fut in as_completed(futures):
            done += 1
            paper = futures[fut]
            try:
                fut.result()
            except Exception as e:
                log.warning("worker failed for %s: %s", paper.title, e)
            if progress:
                progress(done, total, paper)
            if stop and stop(done):
                break
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    return papers
