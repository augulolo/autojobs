"""
Scraper de vacantes de Ford (Oracle HCM Cloud).
ATS: Oracle Fusion (efds.fa.em5.oraclecloud.com)
Site: CX_1
Trae TODAS las vacantes globales del portal.
"""
import re
import time
from datetime import UTC, datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from db import deactivate_stale, init_db, upsert

# Sesión con retry automático para Oracle HCM (respuestas lentas)
_session = requests.Session()
_retry = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retry))
_session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; AutoJobsAR/0.1)",
})

ORACLE_BASE = "https://efds.fa.em5.oraclecloud.com"
SEARCH_URL = (
    f"{ORACLE_BASE}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
)
SITE_NUMBER = "CX_1"
COMPANY = "Ford"
ID_PREFIX = "ford"

MAX_RETRIES_PER_PAGE = 3
REQUEST_TIMEOUT = 45

# Mapeo de códigos de país Oracle → nombre legible
COUNTRY_CODES = {
    "AR": "Argentina", "BR": "Brazil", "MX": "Mexico", "US": "United States",
    "CA": "Canada", "DE": "Germany", "GB": "United Kingdom", "FR": "France",
    "ES": "Spain", "IT": "Italy", "CN": "China", "IN": "India", "JP": "Japan",
    "TH": "Thailand", "ZA": "South Africa", "AU": "Australia", "TR": "Turkey",
    "RO": "Romania", "PT": "Portugal", "VN": "Vietnam", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru",
}


def _fetch_page(offset: int, limit: int) -> list[dict]:
    """Baja una página con retry. Offset va dentro del finder (Oracle HCM)."""
    params = {
        "onlyData": "true",
        "expand": "requisitionList",
        "finder": f"findReqs;siteNumber={SITE_NUMBER},keyword=,offset={offset}",
        "limit": str(limit),
        "offset": "0",
    }
    for attempt in range(1, MAX_RETRIES_PER_PAGE + 1):
        try:
            resp = _session.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return []
            return items[0].get("requisitionList", [])
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            print(f"  [Ford] ⚠ Timeout offset={offset} "
                  f"(intento {attempt}/{MAX_RETRIES_PER_PAGE}): {exc}")
            if attempt < MAX_RETRIES_PER_PAGE:
                time.sleep(3 * attempt)
    print(f"  [Ford] ✘ Saltando página offset={offset}")
    return []


BATCH_SIZE = 500  # guardar en DB cada N vacantes para no acumular todo en RAM


def fetch_and_store() -> tuple[int, set[str]]:
    """Baja TODAS las vacantes paginando y guarda en batches.
    Devuelve (total, set de IDs activos)."""
    offset = 0
    limit = 25
    total = 0
    buffer: list[dict] = []
    all_ids: set[str] = set()
    while True:
        batch = _fetch_page(offset, limit)
        if not batch:
            break
        normalized = [normalize(j) for j in batch]
        buffer.extend(normalized)
        all_ids.update(j["id"] for j in normalized)
        total += len(batch)
        offset += limit
        if len(buffer) >= BATCH_SIZE:
            upsert(buffer)
            print(f"  [Ford] ... {total} descargadas, {len(buffer)} guardadas")
            buffer.clear()
        elif (offset % 200) == 0:
            print(f"  [Ford] ... {total} descargadas")
        if len(batch) < limit:
            break
    # Flush restante
    if buffer:
        upsert(buffer)
    return total, all_ids


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def normalize(job: dict) -> dict:
    """Oracle HCM job → esquema común."""
    job_id = str(job.get("Id", ""))
    short_desc = _strip_html(job.get("ShortDescriptionStr") or "")
    country_code = (job.get("PrimaryLocationCountry") or "").strip()
    country_name = COUNTRY_CODES.get(country_code, country_code)
    return {
        "id": f"{ID_PREFIX}-{job_id}",
        "company": COMPANY,
        "title": (job.get("Title") or "").strip(),
        "location": (job.get("PrimaryLocation") or "").strip(),
        "country": country_name,
        "posted_on": job.get("PostedDate") or "",
        "url": f"{ORACLE_BASE}/hcmUI/CandidateExperience/en/sites/{SITE_NUMBER}/job/{job_id}",
        "area": None,
        "seniority": None,
        "score": None,
        "raw_description": short_desc,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    init_db()
    print(f"  [Ford] Bajando vacantes de Oracle HCM (site {SITE_NUMBER})...")
    total, active_ids = fetch_and_store()
    stale = deactivate_stale(COMPANY, active_ids)
    print(f"  [Ford] {total} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
