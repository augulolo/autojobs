"""
Scraper de vacantes del Grupo Volkswagen (SAP SuccessFactors).
ATS: SAP SuccessFactors (jobs.volkswagen-group.com)
Incluye: VW, Audi, Porsche, SEAT/Cupra, Škoda, Lamborghini, Bentley,
         VW Financial Services, Electrify America, etc.
"""
from db import deactivate_stale, init_db, upsert
from successfactors import scrape_successfactors

BASE_URL = "https://jobs.volkswagen-group.com"
COMPANY = "VW Group"
ID_PREFIX = "vw"


def main() -> None:
    init_db()
    print(f"  [{COMPANY}] Bajando vacantes de SuccessFactors...")
    jobs = scrape_successfactors(
        base_url=BASE_URL,
        company=COMPANY,
        id_prefix=ID_PREFIX,
        per_page=25,
    )
    print(f"  [{COMPANY}] {len(jobs)} vacantes encontradas")
    n = upsert(jobs)
    stale = deactivate_stale(COMPANY, {j["id"] for j in jobs})
    print(f"  [{COMPANY}] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
