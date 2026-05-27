"""
Scraper de vacantes de Scania (SAP SuccessFactors).
ATS: SAP SuccessFactors (jobs.scania.com)
Scania es parte de TRATON Group / Volkswagen AG — opera en Argentina.
"""
from db import deactivate_stale, init_db, upsert
from successfactors import scrape_successfactors

BASE_URL = "https://jobs.scania.com"
COMPANY = "Scania"
ID_PREFIX = "scania"


def main() -> None:
    init_db()
    print(f"  [{COMPANY}] Bajando vacantes de SuccessFactors...")
    jobs = scrape_successfactors(
        base_url=BASE_URL,
        company=COMPANY,
        id_prefix=ID_PREFIX,
        per_page=15,
    )
    print(f"  [{COMPANY}] {len(jobs)} vacantes encontradas")
    n = upsert(jobs)
    stale = deactivate_stale(COMPANY, {j["id"] for j in jobs})
    print(f"  [{COMPANY}] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
