"""
Scraper de vacantes de Stellantis (Empregare).
ATS: Empregare (stellantis.empregare.com)
API JSON: GET /api/{lang}/vagas/buscar-novo?query=stellantis&pagina=N
La API ignora `limit` y `offset`, pagina solo con `pagina=N` (10 items/pág).
Cloudflare rate-limits agresivamente — se usa delay de 2s entre requests.
Incluye: Fiat, Peugeot, Citroën, Jeep, RAM, Chrysler, Dodge, Alfa Romeo, etc.
Total: ~1200 vacantes (mayormente Brasil + Argentina).
"""
import time
from datetime import UTC, datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from db import deactivate_stale, init_db, upsert

BASE_URL = "https://stellantis.empregare.com"
API_PATH = "/api/pt-br/vagas/buscar-novo"
COMPANY = "Stellantis"
ID_PREFIX = "stellantis"

# API siempre devuelve 10 items por página, ignora el param `limit`
ACTUAL_PAGE_SIZE = 10

_session = requests.Session()
_retry = Retry(
    total=5,
    backoff_factor=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retry))
_session.headers.update({
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://stellantis.empregare.com/pt-br/vagas",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
})

COUNTRY_CODES: dict[str, str] = {
    "BR": "Brazil", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "MX": "Mexico", "PT": "Portugal",
    "UY": "Uruguay", "PY": "Paraguay", "PE": "Peru",
}

# Delay entre requests para evitar Cloudflare 403
REQUEST_DELAY = 2.0


def _guess_country(cidades: list[str]) -> str | None:
    """Extrae país del campo cidades (ej: 'Betim, MG, BR')."""
    for city_str in cidades:
        parts = [p.strip() for p in city_str.split(",")]
        if parts:
            code = parts[-1].upper()
            if code in COUNTRY_CODES:
                return COUNTRY_CODES[code]
    return None


def fetch_all() -> list[dict]:
    """Pagina la API de Empregare hasta agotar resultados."""
    all_jobs: list[dict] = []
    seen_ids: set[str] = set()
    page = 1
    total_pages: int | None = None
    consecutive_errors = 0
    max_errors = 5

    while True:
        try:
            resp = _session.get(
                f"{BASE_URL}{API_PATH}",
                params={"query": "stellantis", "pagina": page},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            consecutive_errors = 0
        except (requests.RequestException, ValueError) as e:
            consecutive_errors += 1
            print(f"  [{COMPANY}] ⚠ Error en página {page}: {e}")
            if consecutive_errors >= max_errors:
                print(f"  [{COMPANY}] ✗ {max_errors} errores consecutivos, abortando")
                break
            # Back off más agresivo en error
            time.sleep(REQUEST_DELAY * 3)
            continue

        model = data.get("model", {})
        if total_pages is None:
            total_pages = model.get("totalRegistro", 0)
            total_vagas = model.get("totalVagas", 0)
            print(f"  [{COMPANY}] Total vacantes: {total_vagas}, páginas: {total_pages}")

        batch = model.get("dados", [])
        if not batch:
            break

        now = datetime.now(UTC).isoformat()
        new_in_page = 0
        for raw in batch:
            job_id = str(raw.get("id", ""))
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            new_in_page += 1
            cidades = raw.get("cidades") or []
            location = "; ".join(cidades) if cidades else ""
            all_jobs.append({
                "id": f"{ID_PREFIX}-{job_id}",
                "company": COMPANY,
                "title": (raw.get("titulo") or "").strip().rstrip("|").strip(),
                "location": location,
                "country": _guess_country(cidades),
                "posted_on": raw.get("data", ""),
                "url": f"{BASE_URL}/{raw.get('url', '')}",
                "area": None,
                "seniority": None,
                "score": None,
                "raw_description": raw.get("chamada", ""),
                "scraped_at": now,
            })

        # Si toda la página fue duplicados, la API dejó de paginar
        if new_in_page == 0:
            print(f"  [{COMPANY}] Página {page} sin resultados nuevos, cortando")
            break

        page += 1
        if total_pages and page > total_pages:
            break

        # Progreso cada 100 vacantes
        if len(all_jobs) % 100 < ACTUAL_PAGE_SIZE:
            print(f"  [{COMPANY}] ... {len(all_jobs)} vacantes bajadas")

        time.sleep(REQUEST_DELAY)

    return all_jobs


def main() -> None:
    init_db()
    print(f"  [{COMPANY}] Bajando vacantes de Empregare...")
    jobs = fetch_all()
    print(f"  [{COMPANY}] {len(jobs)} vacantes encontradas")
    n = upsert(jobs)
    stale = deactivate_stale(COMPANY, {j["id"] for j in jobs})
    print(f"  [{COMPANY}] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
