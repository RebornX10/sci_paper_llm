import requests

from app.config import CONFIG

SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": f"sci_paper_llm/1.0 (mailto:{CONFIG['openalex']['mailto']})"}
)
# Pool must comfortably exceed the download worker ceiling (io_workers_cap) so
# concurrent downloads reuse keep-alive connections instead of churning sockets.
_pool = max(128, int(CONFIG["download"].get("io_workers_cap", 32)) * 2)
_adapter = requests.adapters.HTTPAdapter(pool_connections=_pool, pool_maxsize=_pool)
SESSION.mount("https://", _adapter)
SESSION.mount("http://", _adapter)

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
