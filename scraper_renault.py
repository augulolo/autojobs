"""
Scraper de vacantes de Renault (Workday CXS API).
Tenant: alliancewd | Subdomain: wd3 | Site: renault-group-careers
Trae TODAS las vacantes globales del portal.
"""
from db import deactivate_stale, init_db, upsert
from workday import scrape_workday

WORKDAY_BASE = "https://alliancewd.wd3.myworkdayjobs.com"
TENANT = "alliancewd"
SITE = "renault-group-careers"
COMPANY = "Renault"
ID_PREFIX = "renault"


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
    print(f"  [Renault] {n} vacantes guardadas, {stale} desactivadas")


if __name__ == "__main__":
    main()
