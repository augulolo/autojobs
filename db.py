"""
Módulo compartido de persistencia SQLite para AutoJobs AR.
Todos los scrapers usan init_db() y upsert() de acá.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/jobs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    country TEXT,
    posted_on TEXT,
    url TEXT,
    area TEXT,
    seniority TEXT,
    score INTEGER,
    raw_description TEXT,
    scraped_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
"""

MIGRATION_ADD_COUNTRY = "ALTER TABLE jobs ADD COLUMN country TEXT"
MIGRATION_ADD_ACTIVE = "ALTER TABLE jobs ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"


def init_db(db_path: Path = DB_PATH) -> None:
    """Crea la tabla jobs si no existe y aplica migraciones."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    # Migraciones: agregar columnas faltantes
    cols = [row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()]
    if "country" not in cols:
        conn.execute(MIGRATION_ADD_COUNTRY)
    if "is_active" not in cols:
        conn.execute(MIGRATION_ADD_ACTIVE)
    conn.commit()
    conn.close()


def upsert(jobs: list[dict], db_path: Path = DB_PATH) -> int:
    """Inserta o actualiza. Devuelve cuántas filas procesó."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for job in jobs:
        cur.execute("""
            INSERT INTO jobs (id, company, title, location, country, posted_on, url,
                              area, seniority, score, raw_description, scraped_at,
                              is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                location = excluded.location,
                country = excluded.country,
                posted_on = excluded.posted_on,
                url = excluded.url,
                raw_description = excluded.raw_description,
                scraped_at = excluded.scraped_at,
                is_active = 1
        """, (
            job["id"], job["company"], job["title"], job["location"],
            job.get("country"), job["posted_on"], job["url"], job["area"],
            job["seniority"], job["score"], job["raw_description"],
            job["scraped_at"],
        ))
    conn.commit()
    conn.close()
    return len(jobs)


def deactivate_stale(company: str, active_ids: set[str],
                     db_path: Path = DB_PATH) -> int:
    """Marca como inactivas las vacantes de `company` que ya no están en el scrape.
    Devuelve cuántas se desactivaron."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if not active_ids:
        conn.close()
        return 0
    placeholders = ",".join("?" for _ in active_ids)
    cur.execute(f"""
        UPDATE jobs SET is_active = 0
        WHERE company = ? AND is_active = 1
        AND id NOT IN ({placeholders})
    """, (company, *active_ids))
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n
