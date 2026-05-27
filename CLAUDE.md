# AutoJobs

Dashboard de vacantes del sector automotriz global, scoreadas según perfil
objetivo: graduado en Admin de Empresas (UdeSA) cursando Master en Finanzas.
Areas de interés: finanzas, control de gestión, comercial, estrategia, planning.

## Stack
- Python 3.11+
- requests, pandas, streamlit, pytest
- SQLite local en `data/jobs.db`

## Comandos
- `python run_all.py` — corre todos los scrapers + scoring (~90 seg)
- `python scraper_toyota.py` — Toyota global (Workday wd503/TLAC)
- `python scraper_renault.py` — Renault global (Workday alliancewd.wd3)
- `python scraper_nissan.py` — Nissan global (Workday alliance.wd3)
- `python scraper_ford.py` — Ford global (Oracle HCM)
- `python scraper_honda.py` — Honda Argentina (HiringRoom)
- `python scraper_vw.py` — VW Group global (SAP SuccessFactors)
- `python scraper_scania.py` — Scania global (SAP SuccessFactors)
- `python scoring.py` — clasifica area/seniority y calcula score 0-100
- `streamlit run app.py` — levanta dashboard en localhost:8501
- `python -m pytest tests/ -v` — corre tests

## Arquitectura

### Módulos compartidos
- `db.py` — schema SQLite, `init_db()`, `upsert()`, migración automática
- `workday.py` — helper para scrapers Workday CXS: paginación rápida (sin
  fetch de detalle), normalización, detección de país por heurística de
  localización
- `successfactors.py` — helper para scrapers SAP SuccessFactors: parseo HTML
  server-side, soporta layout tabla (VW) y tiles (Scania), paginación por
  startrow, detección de país por código ISO al final del location

### Scrapers
Cada empresa tiene `scraper_<empresa>.py` con una función `main()`.
- **Workday** (Toyota, Renault, Nissan): usan `workday.scrape_workday()`.
  Modo rápido: solo pagina listings, no fetchea detalle individual.
- **Oracle HCM** (Ford): lógica propia con REST API + retry + batched
  persistence. Paginación via offset dentro del finder param.
- **HiringRoom** (Honda): POST al endpoint de HiringRoom con form data,
  devuelve HTML parcial. Parseo con regex. Dedup por vacancy_id.
- **SAP SuccessFactors** (VW Group, Scania): usan
  `successfactors.scrape_successfactors()`. Parsea HTML renderizado por
  servidor con paginación via `startrow` param.

### Pipeline
`run_all.py` orquesta: importa cada scraper, llama a `main()`, luego scoring.
El GitHub Action (`.github/workflows/scrape.yml`) lo corre diariamente a las
08:00 ART.

## Esquema de la tabla `jobs`
id, company, title, location, country, posted_on, url, area, seniority,
score, raw_description, scraped_at

## Convenciones
- Type hints en todo. Funciones puras siempre que se pueda.
- Errores de red: logueá y seguí, no abortes el batch completo.
- Antes de agregar un conector nuevo, verificá la fuente real (no asumas
  endpoints) y dejá una nota en el README sobre el ATS que usa esa empresa.
- Nada de datos inventados ni en mocks ni en tests. Si necesitás fixtures,
  guardá responses reales en `tests/fixtures/`.
- Mantené `requirements.txt` mínimo. Cualquier dep nueva, justificala.

## ATS investigados
- Toyota: Workday wd503/TLAC (~350 vacantes globales)
- Renault: Workday alliancewd.wd3/renault-group-careers (~494 globales)
- Nissan: Workday alliance.wd3/nissanjobs (~353 globales)
- Ford: Oracle HCM efds.fa.em5.oraclecloud.com/CX_1 (~785 globales)
- Honda: HiringRoom hondamotorargentina.hiringroom.com (~20 Argentina)
- VW Group: SAP SuccessFactors jobs.volkswagen-group.com (~180 globales)
- Scania: SAP SuccessFactors jobs.scania.com (~713 globales)
- Stellantis: portal sin jobs accesibles (0 resultados en múltiples APIs)
- BMW/Mercedes/IVECO/Hyundai/Kia/BYD: sin portal público accesible

## Pendiente
- Monitorear si Stellantis habilita career site público
- Tests del scraper (mocks de responses)
- Alertas cuando aparece una vacante con score > 70
