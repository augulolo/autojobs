"""
Scraper de vacantes de Nissan (Workday CXS API).
Tenant: alliance | Subdomain: wd3 | Site: nissanjobs
Trae TODAS las vacantes globales del portal.
"""
from db import deactivate_stale, init_db, upsert
from workday import scrape_workday

WORKDAY_BASE = "https://alliance.wd3.myworkdayjobs.com"
TENANT = "alliance"
SITE = "nissanjobs"
COMPANY = "Nissan"
ID_PREFIX = "nissan"


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
    print(f"  [Nissan] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
