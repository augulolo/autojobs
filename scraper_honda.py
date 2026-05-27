"""
Scraper de vacantes de Honda Argentina (HiringRoom).
ATS: HiringRoom (hondamotorargentina.hiringroom.com)
Endpoint: POST /jobs/getVacanciesForPortal/ devuelve HTML parcial.
"""
import re
from datetime import UTC, datetime
from html import unescape

import requests

from db import deactivate_stale, init_db, upsert

BASE_URL = "https://hondamotorargentina.hiringroom.com"
COMPANY = "Honda"
ID_PREFIX = "honda"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AutoJobsAR/0.1)",
    "X-Requested-With": "XMLHttpRequest",
}


def fetch_all() -> list[dict]:
    """Pagina el listado de HiringRoom hasta agotar resultados."""
    all_jobs: list[dict] = []
    seen_ids: set[str] = set()
    page = 1
    while True:
        try:
            resp = requests.post(
                f"{BASE_URL}/jobs/getVacanciesForPortal/",
                data={"searchText": "", "typePortal": "external", "page": page},
                headers=HEADERS,
                timeout=15,
            )
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  [Honda] ⚠ Error en página {page}: {e}")
            break

        if data.get("result") != "success":
            break

        html = data.get("data", {}).get("htmlContent", "")
        if not html.strip():
            break

        # Parsear tarjetas de vacantes del HTML
        vacancy_ids = re.findall(r'get_vacancy/([a-f0-9]+)', html)
        titles = re.findall(r'name__vacancy[^>]*>([^<]+)', html)
        cards = list(zip(vacancy_ids, titles))
        if not cards:
            break

        new_count = 0
        for vacancy_id, title in cards:
            full_id = f"{ID_PREFIX}-{vacancy_id}"
            if full_id in seen_ids:
                continue
            seen_ids.add(full_id)
            new_count += 1
            all_jobs.append({
                "id": full_id,
                "company": COMPANY,
                "title": unescape(title.strip()),
                "location": "Campana, Buenos Aires, Argentina",
                "country": "Argentina",
                "posted_on": "",
                "url": f"{BASE_URL}/jobs/get_vacancy/{vacancy_id}",
                "area": None,
                "seniority": None,
                "score": None,
                "raw_description": "",
                "scraped_at": datetime.now(UTC).isoformat(),
            })

        # Si no hubo IDs nuevos, dejamos de paginar (HiringRoom repite)
        if new_count == 0:
            break

        page += 1
        if len(cards) < 20:
            break

    return all_jobs


def main() -> None:
    init_db()
    print(f"  [Honda] Bajando vacantes de HiringRoom...")
    jobs = fetch_all()
    print(f"  [Honda] {len(jobs)} vacantes encontradas")
    n = upsert(jobs)
    stale = deactivate_stale(COMPANY, {j["id"] for j in jobs})
    print(f"  [Honda] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
