"""
Helper compartido para scrapers de Workday CXS API.
Modo rápido: pagina el listado y normaliza directo (sin fetch de detalle).
Trae TODAS las vacantes sin filtrar por país.
"""
import re
from datetime import UTC, datetime

import requests

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; AutoJobsAR/0.1)",
}


def fetch_all_jobs(base_url: str, tenant: str, site: str, limit: int = 20) -> list[dict]:
    """Pagina el endpoint CXS hasta agotar resultados."""
    url = f"{base_url}/wday/cxs/{tenant}/{site}/jobs"
    all_jobs: list[dict] = []
    offset = 0
    while True:
        body = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        try:
            resp = requests.post(url, json=body, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  ⚠ Error paginando offset={offset}: {e}")
            break
        data = resp.json()
        batch = data.get("jobPostings", [])
        if not batch:
            break
        all_jobs.extend(batch)
        offset += limit
        if len(batch) < limit:
            break
    return all_jobs


# Mapeo de hints en locationsText → país normalizado
_COUNTRY_HINTS: list[tuple[str, list[str]]] = [
    ("Argentina", ["argentina", "zarate", "zárate", "capital federal", "buenos aires",
                   "sta isabel", "hor_argentina"]),
    ("Brazil", ["brasil", "brazil", "sorocaba", "porto feliz", "indaiatuba",
                "toyota do brasil", "centro de distribuição", "rio de janeiro",
                "resende", "são paulo", "sao paulo", "são josé dos pinhais"]),
    ("Mexico", ["mexico", "méxico", "aguascalientes"]),
    ("United States", ["united states", "usa", "texas", "california", "tennessee",
                       "plano", "irvine", "franklin", "santa clara", "smyrna",
                       "irving", "atlanta", "georgia", "jacksonville", "miami",
                       "houston", ", fl", ", tx", ", ny", ", ca"]),
    ("Canada", ["canada", "ontario", "quebec", "alberta", "mississauga",
                "calgary", "kirkland"]),
    ("Japan", ["japan", "atsugi", "oppama", "zama", "tochigi", "yokohama",
               "nissan technical center", "nissan advanced technology",
               "global headquarters", "kokunai"]),
    ("India", ["india", "chennai", "gurgaon", "pune", "mumbai", "rntbci",
               "trivandrum", ", in"]),
    ("France", ["france", "paris", "boulogne", "flins", "guyancourt",
                "aubergenville", "aubevoye", "batilly", "cléon", "cleon",
                "douai", "foucheres", "lardy", "le havre", "le mans",
                "le plessis", "maubeuge", "montigny", "noisy", "pessac",
                "puiseux", "ruitz", "saint andre", "toulouse", "val de fontenay",
                "valbonne", "villeurbanne", "fr_ren"]),
    ("Spain", ["spain", "españa", "madrid", "barcelona", "valladolid"]),
    ("United Kingdom", ["united kingdom", "uk", "london", "sunderland",
                        "enstone", "maple cross", "gb_renault"]),
    ("Germany", ["germany", "deutschland", "munich", "münchen", "stuttgart"]),
    ("Thailand", ["thailand", "asean office"]),
    ("Romania", ["romania", "bucharest", "pitesti", "bucuresti", "mioveni",
                 "titu", "oarja", "ro_ren"]),
    ("Turkey", ["turkey", "türkiye", "istanbul"]),
    ("South Korea", ["korea", "seoul"]),
    ("China", ["china", "beijing", "shanghai", "hangzhou"]),
    ("Colombia", ["colombia", "bogotá", "bogota", "envigado"]),
    ("Chile", ["chile", "santiago"]),
    ("Netherlands", ["netherlands", "amsterdam"]),
    ("Italy", ["italy", "italia", "torino", "turin"]),
    ("South Africa", ["south africa"]),
    ("Australia", ["australia", "melbourne", "sydney"]),
    ("Morocco", ["morocco", "maroc", "tangier", "tanger"]),
    ("Ireland", ["ireland", "dublin"]),
    ("Tunisia", ["tunisia", "tunis"]),
    ("Malta", ["malta", "st julian"]),
]


def _guess_country(locations_text: str) -> str | None:
    """Extrae país del texto de ubicación usando hints conocidos."""
    if not locations_text:
        return None
    text = locations_text.lower()
    # Formato "City, State - Country" (Nissan style)
    if " - " in text:
        after_dash = text.rsplit(" - ", 1)[-1].strip()
        for country, hints in _COUNTRY_HINTS:
            if any(h in after_dash for h in hints):
                return country
    # Búsqueda general por hints
    for country, hints in _COUNTRY_HINTS:
        if any(h in text for h in hints):
            return country
    return None


def normalize_job_from_listing(
    job: dict,
    *,
    company: str,
    id_prefix: str,
    base_url: str,
    site: str,
) -> dict:
    """Workday listing item → esquema común (sin fetch de detalle)."""
    external_path = job.get("externalPath", "")
    job_id = external_path.rsplit("/", 1)[-1] or job.get("bulletFields", [""])[0]
    locations_text = (job.get("locationsText") or "").strip()
    # Fallback: algunos Workday ponen la ciudad en bulletFields[0]
    bullet_fields = job.get("bulletFields") or []
    if not locations_text and bullet_fields:
        locations_text = bullet_fields[0]
    return {
        "id": f"{id_prefix}-{job_id}",
        "company": company,
        "title": (job.get("title") or "").strip(),
        "location": locations_text,
        "country": _guess_country(locations_text),
        "posted_on": job.get("postedOn") or "",
        "url": f"{base_url}/es/{site}{external_path}",
        "area": None,
        "seniority": None,
        "score": None,
        "raw_description": "",  # sin detalle, scoring usa título
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def scrape_workday(
    *,
    base_url: str,
    tenant: str,
    site: str,
    company: str,
    id_prefix: str,
) -> list[dict]:
    """
    Pipeline rápido de scraping Workday:
    1. Pagina listado completo
    2. Normaliza todas las vacantes (sin filtrar por país)
    """
    print(f"  [{company}] Bajando listado de {site}...")
    raw = fetch_all_jobs(base_url, tenant, site)
    print(f"  [{company}] {len(raw)} vacantes en listado")

    normalized = [
        normalize_job_from_listing(
            job,
            company=company,
            id_prefix=id_prefix,
            base_url=base_url,
            site=site,
        )
        for job in raw
    ]
    return normalized
