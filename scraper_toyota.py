"""
Scraper de vacantes de Toyota (Workday CXS API).
Tenant: toyota | Subdomain: wd503 | Site: TLAC (Toyota Latin America & Caribbean)
Trae TODAS las vacantes globales del portal.
"""
from db import deactivate_stale, init_db, upsert
from workday import scrape_workday

WORKDAY_BASE = "https://toyota.wd503.myworkdayjobs.com"
TENANT = "toyota"
SITE = "TLAC"
COMPANY = "Toyota"
ID_PREFIX = "toyota"


def main() -> None:
    init_db()
    jobs = scrape_workday(
        base_url=WORKDAY_BASE,
        tenant=TENANT,
        site=SITE,
        company=COMPANY,
        id_prefix=ID_PREFIX,
    )
    n = upsert(jobs)
    stale = deactivate_stale(COMPANY, {j["id"] for j in jobs})
    print(f"  [Toyota] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
