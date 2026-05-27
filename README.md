# AutoJobs

Dashboard local para visualizar vacantes del sector automotriz global,
scoreadas según perfil de admin + finanzas. Filtros por empresa, país,
area, seniority y búsqueda libre.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

## Uso

```bash
# Correr todos los scrapers + scoring de una vez (~90 segundos)
python run_all.py

# O individualmente:
python scraper_toyota.py
python scraper_renault.py
python scraper_nissan.py
python scraper_ford.py
python scraper_honda.py
python scraper_vw.py
python scraper_scania.py
python scraper_stellantis.py
python scoring.py

# Abrir dashboard
streamlit run app.py
```

El GitHub Action `.github/workflows/scrape.yml` corre `run_all.py` todos los
días a las 08:00 ART y commitea el `.db` actualizado.

## Estructura

| Archivo | Rol |
|---|---|
| `db.py` | Módulo compartido: schema, `init_db()`, `upsert()` |
| `workday.py` | Helper para scrapers Workday CXS (paginación rápida) |
| `successfactors.py` | Helper para scrapers SAP SuccessFactors (HTML parsing) |
| `scraper_toyota.py` | Toyota — Workday wd503/TLAC |
| `scraper_renault.py` | Renault — Workday alliancewd.wd3/renault-group-careers |
| `scraper_nissan.py` | Nissan — Workday alliance.wd3/nissanjobs |
| `scraper_ford.py` | Ford — Oracle HCM Cloud (efds.fa.em5.oraclecloud.com) |
| `scraper_honda.py` | Honda — HiringRoom (hondamotorargentina.hiringroom.com) |
| `scraper_vw.py` | VW Group — SAP SuccessFactors (jobs.volkswagen-group.com) |
| `scraper_scania.py` | Scania — SAP SuccessFactors (jobs.scania.com) |
| `scraper_stellantis.py` | Stellantis — Empregare (stellantis.empregare.com) |
| `scoring.py` | Clasifica area/seniority y calcula score 0-100 vs perfil |
| `app.py` | Dashboard Streamlit con filtros, KPIs, gráficos y tabla |
| `run_all.py` | Orquestador: corre todos los scrapers + scoring |
| `data/jobs.db` | SQLite local (se crea automáticamente) |

## ATS por empresa

| Empresa | ATS | Endpoint | Vacantes |
|---|---|---|---|
| Toyota | Workday | wd503 / TLAC | ~350 |
| Renault | Workday | alliancewd.wd3 / renault-group-careers | ~494 |
| Nissan | Workday | alliance.wd3 / nissanjobs | ~353 |
| Ford | Oracle HCM | efds.fa.em5.oraclecloud.com / CX_1 | ~785 |
| Honda | HiringRoom | hondamotorargentina.hiringroom.com | ~20 |
| VW Group | SAP SuccessFactors | jobs.volkswagen-group.com | ~180 |
| Scania | SAP SuccessFactors | jobs.scania.com | ~713 |
| Stellantis | Empregare | stellantis.empregare.com / buscar-novo | ~70 |
| BMW | Sin ATS público | — | No scrapeable |
| Mercedes-Benz | Sin ATS público | — | No scrapeable |
| IVECO/CNH | Sin portal accesible | — | No scrapeable |
| Hyundai/Kia | Sin portal accesible | — | No scrapeable |

## Esquema de la tabla `jobs`

```sql
id              TEXT PRIMARY KEY     -- "{empresa}-{id_proveedor}"
company         TEXT NOT NULL
title           TEXT NOT NULL
location        TEXT                 -- ubicación textual del ATS
country         TEXT                 -- país normalizado (heurística)
posted_on       TEXT                 -- formato varía por ATS
url             TEXT                 -- link directo para postular
area            TEXT                 -- Finanzas / Comercial / Estrategia / Ingeniería / etc
seniority       TEXT                 -- Trainee / Junior / SSr / Senior / Lead
score           INTEGER              -- 0-100
raw_description TEXT
scraped_at      TEXT NOT NULL        -- ISO UTC
is_active       INTEGER DEFAULT 1    -- 0 = ya no está publicada
```

## Dashboard

Filtros disponibles en la sidebar:
- Toggle vacantes activas / todas (incluye inactivas)
- Búsqueda libre por título
- Empresa
- País
- Area (Finanzas, Comercial, Estrategia, IT, RRHH, Operaciones, Ingeniería, Legal, Comunicación)
- Seniority (Trainee, Junior, SSr, Senior, Lead)
- Score mínimo
- Exportar a CSV (botón en la tabla)

## Agregar nuevas empresas

1. Identificar el ATS (Workday, Oracle HCM, SAP SuccessFactors, etc.)
2. Si es Workday: crear `scraper_<empresa>.py` usando `workday.scrape_workday()`
3. Si es SuccessFactors: crear scraper usando `successfactors.scrape_successfactors()`
4. Si es otro ATS: implementar lógica propia con retry + `normalize()` + `upsert()`
5. Importar `init_db()`, `upsert()` y `deactivate_stale()` de `db.py`
6. Agregar el módulo a `SCRAPERS` en `run_all.py`
7. Si el ATS no tiene campo de país, agregar hints de ciudades en
   `_COUNTRY_HINTS` de `workday.py` o `successfactors.py`

## Tests

```bash
python -m pytest tests/ -v
```
