"""
Helper compartido para scrapers de SAP SuccessFactors career sites.
Parsea HTML renderizado por servidor con paginación via startrow.
Soporta dos layouts: tabla (VW Group) y tiles (Scania).
"""
import re
import time
from datetime import UTC, datetime
from html import unescape

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session = requests.Session()
_retry = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retry))
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; AutoJobsAR/0.1)",
    "Accept": "text/html,application/xhtml+xml",
})

# ---------------------------------------------------------------------------
# Country hints (reutiliza la lógica de workday.py ampliada)
# ---------------------------------------------------------------------------
_COUNTRY_CODES: dict[str, str] = {
    "AR": "Argentina", "BR": "Brazil", "MX": "Mexico", "US": "United States",
    "CA": "Canada", "DE": "Germany", "GB": "United Kingdom", "FR": "France",
    "ES": "Spain", "IT": "Italy", "CN": "China", "IN": "India", "JP": "Japan",
    "TH": "Thailand", "ZA": "South Africa", "AU": "Australia", "TR": "Turkey",
    "RO": "Romania", "PT": "Portugal", "VN": "Vietnam", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "SE": "Sweden", "NO": "Norway",
    "NL": "Netherlands", "BE": "Belgium", "PL": "Poland", "CZ": "Czech Republic",
    "AT": "Austria", "CH": "Switzerland", "DK": "Denmark", "FI": "Finland",
    "KR": "South Korea", "TW": "Taiwan", "SG": "Singapore", "MY": "Malaysia",
    "ID": "Indonesia", "PH": "Philippines", "HU": "Hungary", "SK": "Slovakia",
    "SI": "Slovenia", "HR": "Croatia", "RS": "Serbia", "BG": "Bulgaria",
    "LT": "Lithuania", "LV": "Latvia", "EE": "Estonia", "IE": "Ireland",
    "GR": "Greece", "RU": "Russia", "UA": "Ukraine", "KE": "Kenya",
    "NG": "Nigeria", "EG": "Egypt", "MA": "Morocco", "TN": "Tunisia",
    "SA": "Saudi Arabia", "AE": "UAE", "IL": "Israel", "NZ": "New Zealand",
}

_COUNTRY_HINTS: list[tuple[str, list[str]]] = [
    ("Argentina", ["argentina", ", ar", "buenos aires", "trenque lauquen",
                   "tucumán", "tucuman"]),
    ("Brazil", ["brazil", "brasil", ", br"]),
    ("Germany", ["germany", "deutschland", ", de", "münchen", "munich",
                 "stuttgart", "berlin", "hamburg", "frankfurt", "wolfsburg",
                 "aachen", "koblenz", "ingolstadt"]),
    ("Sweden", ["sweden", "sverige", ", se", "södertälje", "sodertalje",
                "stockholm", "luleå", "lulea", "malmö", "malmo", "gothenburg"]),
    ("United States", ["united states", "usa", ", us"]),
    ("Belgium", ["belgium", ", be", "oudsbergen"]),
    ("Netherlands", ["netherlands", ", nl", "amsterdam", "eindhoven", "zwolle"]),
    ("Norway", ["norway", "norge", ", no", "oslo"]),
    ("Switzerland", ["switzerland", ", ch", "uetendorf"]),
    ("South Africa", ["south africa", ", za", "wingfield"]),
    ("France", ["france", ", fr", "paris", "lyon"]),
    ("United Kingdom", ["united kingdom", "uk", ", gb"]),
    ("Italy", ["italy", "italia", ", it", "milano", "milan", "torino"]),
    ("Spain", ["spain", "españa", ", es", "madrid", "barcelona"]),
    ("Poland", ["poland", "polska", ", pl"]),
    ("Czech Republic", ["czech", ", cz"]),
    ("Denmark", ["denmark", "danmark", ", dk"]),
    ("Finland", ["finland", "suomi", ", fi"]),
    ("Australia", ["australia", ", au"]),
    ("China", ["china", ", cn", "beijing", "shanghai"]),
    ("India", ["india", ", in", "bangalore", "pune"]),
    ("Japan", ["japan", ", jp", "tokyo"]),
    ("South Korea", ["korea", ", kr"]),
    ("Thailand", ["thailand", ", th"]),
    ("Turkey", ["turkey", "türkiye", ", tr"]),
    ("Mexico", ["mexico", "méxico", ", mx"]),
    ("Colombia", ["colombia", ", co"]),
    ("Chile", ["chile", ", cl"]),
]


def _guess_country(location_text: str) -> str | None:
    """Extrae país del texto o código de 2 letras al final."""
    if not location_text:
        return None
    text = location_text.strip()
    # Probar código de 2 letras al final (ej: "Carlo-Schmid-Str. 5, 52146 Wür, DE")
    parts = text.rsplit(",", 1)
    if len(parts) == 2:
        code = parts[1].strip().upper()
        if code in _COUNTRY_CODES:
            return _COUNTRY_CODES[code]
    # Probar código suelto (ej: "US" solo)
    code = text.strip().upper()
    if code in _COUNTRY_CODES:
        return _COUNTRY_CODES[code]
    # Hints textuales
    lower = text.lower()
    for country, hints in _COUNTRY_HINTS:
        if any(h in lower for h in hints):
            return country
    return None


def _strip_tags(html: str) -> str:
    """Remueve tags HTML y normaliza espacios."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Layout 1: Tabla (<tr class="data-row">) — VW Group
# ---------------------------------------------------------------------------
_RE_TABLE_ROW = re.compile(
    r'<tr\s+class="data-row">(.*?)</tr>',
    re.DOTALL,
)
_RE_TITLE_LINK = re.compile(
    r'<a\s+href="([^"]+)"\s+class="jobTitle-link">([^<]+)</a>',
    re.DOTALL,
)
_RE_FACILITY = re.compile(
    r'<span\s+class="jobFacility">([^<]+)</span>',
    re.DOTALL,
)
_RE_DEPARTMENT = re.compile(
    r'<span\s+class="jobDepartment">([^<]+)</span>',
    re.DOTALL,
)
_RE_LOCATION = re.compile(
    r'<span\s+class="jobLocation">\s*([^<]+?)\s*</span>',
    re.DOTALL,
)
_RE_DATE = re.compile(
    r'<span\s+class="jobDate">\s*([^<]+?)\s*</span>',
    re.DOTALL,
)


def _parse_table_page(html: str) -> list[dict]:
    """Parsea rows de tipo tabla (VW Group layout)."""
    jobs = []
    for row_html in _RE_TABLE_ROW.findall(html):
        title_m = _RE_TITLE_LINK.search(row_html)
        if not title_m:
            continue
        href, title = title_m.group(1), unescape(title_m.group(2).strip())
        # Extraer ID numérico del href: /BRAND/job/SLUG/ID/
        job_id = href.rstrip("/").rsplit("/", 1)[-1]
        facility = ""
        m = _RE_FACILITY.search(row_html)
        if m:
            facility = unescape(m.group(1).strip())
        department = ""
        m = _RE_DEPARTMENT.search(row_html)
        if m:
            department = unescape(m.group(1).strip())
        location = ""
        m = _RE_LOCATION.search(row_html)
        if m:
            location = unescape(m.group(1).strip())
        date = ""
        m = _RE_DATE.search(row_html)
        if m:
            date = unescape(m.group(1).strip())
        jobs.append({
            "_id": job_id,
            "_href": href,
            "title": title,
            "facility": facility,
            "department": department,
            "location": location,
            "date": date,
        })
    return jobs


# ---------------------------------------------------------------------------
# Layout 2: Tiles (<li class="job-tile">) — Scania
# ---------------------------------------------------------------------------
_RE_TILE = re.compile(
    r'<li\s+class="job-tile\s+job-id-(\d+)[^"]*"[^>]*data-url="([^"]*)"[^>]*>(.*?)</li>',
    re.DOTALL,
)
_RE_TILE_TITLE = re.compile(
    r'class="jobTitle-link[^"]*"[^>]*href="[^"]*"[^>]*>\s*([^<]+?)\s*</a>',
    re.DOTALL,
)
_RE_SECTION_VALUE = re.compile(
    r'id="job-\d+-desktop-section-(\w+)-value"[^>]*>([^<]+)',
    re.DOTALL,
)


def _parse_tile_page(html: str) -> list[dict]:
    """Parsea tiles (Scania layout)."""
    jobs = []
    for job_id, data_url, tile_html in _RE_TILE.findall(html):
        title_m = _RE_TILE_TITLE.search(tile_html)
        if not title_m:
            continue
        title = unescape(title_m.group(1).strip())
        # Extraer campos del desktop section
        fields: dict[str, str] = {}
        for field_name, value in _RE_SECTION_VALUE.findall(tile_html):
            fields[field_name] = unescape(value.strip())
        jobs.append({
            "_id": job_id,
            "_href": unescape(data_url),
            "title": title,
            "facility": fields.get("facility", ""),
            "department": fields.get("department", ""),
            "location": fields.get("location", ""),
            "date": fields.get("date", ""),
        })
    return jobs


# ---------------------------------------------------------------------------
# Autodetección de layout
# ---------------------------------------------------------------------------
def _detect_and_parse(html: str) -> list[dict]:
    """Detecta layout y parsea."""
    if '<tr class="data-row">' in html:
        return _parse_table_page(html)
    if 'class="job-tile ' in html:
        return _parse_tile_page(html)
    return []


# ---------------------------------------------------------------------------
# Total count
# ---------------------------------------------------------------------------
_RE_TOTAL_TABLE = re.compile(r'Results\s+(?:<b>)?\d+(?:</b>)?\s*[–—-]\s*(?:<b>)?\d+(?:</b>)?\s+of\s+(?:<b>)?(\d+)(?:</b>)?')
_RE_TOTAL_TILE = re.compile(r'jobRecordsFound:\s*parseInt\("(\d+)"\)')


def _extract_total(html: str) -> int | None:
    m = _RE_TOTAL_TABLE.search(html)
    if m:
        return int(m.group(1))
    m = _RE_TOTAL_TILE.search(html)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def scrape_successfactors(
    *,
    base_url: str,
    company: str,
    id_prefix: str,
    per_page: int = 25,
    max_jobs: int = 5000,
) -> list[dict]:
    """
    Scrapea un sitio SAP SuccessFactors paginando HTML.
    Devuelve lista de dicts en esquema jobs común.
    """
    all_jobs: list[dict] = []
    startrow = 0
    total: int | None = None

    while True:
        url = f"{base_url}/search/?q=&sortColumn=referencedate&sortDirection=desc&startrow={startrow}"
        try:
            resp = _session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [{company}] ⚠ Error en startrow={startrow}: {e}")
            break

        html = resp.text
        if total is None:
            total = _extract_total(html)
            if total:
                print(f"  [{company}] Total reportado: {total}")

        batch = _detect_and_parse(html)
        if not batch:
            break

        now = datetime.now(UTC).isoformat()
        for raw in batch:
            job_id = raw["_id"]
            loc = raw["location"]
            all_jobs.append({
                "id": f"{id_prefix}-{job_id}",
                "company": company,
                "title": raw["title"],
                "location": loc,
                "country": _guess_country(loc),
                "posted_on": raw["date"],
                "url": f"{base_url}{raw['_href']}",
                "area": None,
                "seniority": None,
                "score": None,
                "raw_description": raw.get("department", ""),
                "scraped_at": now,
            })

        startrow += len(batch)
        if startrow >= max_jobs:
            print(f"  [{company}] Límite de {max_jobs} alcanzado")
            break
        if total and startrow >= total:
            break
        # Pequeña pausa para no saturar el servidor
        time.sleep(0.5)

    return all_jobs
