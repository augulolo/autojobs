"""Tests de scoring.py usando títulos y descripciones reales de Toyota Argentina."""
import sqlite3
from pathlib import Path

import pytest

from scoring import detect_area, detect_seniority, enrich_all, score_job

# ── Títulos reales de Toyota AR (scraped 2026-05-26) ───────────────────────

REAL_JOBS = [
    {
        "title": "JR Finance Analyst",
        "desc": "Analizar y consolidar información financiera para reportes mensuales. "
                "Participar en el proceso de presupuesto y forecast. "
                "Análisis de variaciones y KPI financieros. Control de gestión.",
        "expected_area": "Finanzas",
        "expected_seniority": "Junior",
    },
    {
        "title": "Asesor Comercial - LEXUS",
        "desc": "Gestionar la cartera de clientes premium. Estrategia comercial "
                "y pricing de vehículos. Responsable del proceso de ventas.",
        "expected_area": "Comercial",
        "expected_seniority": None,
    },
    {
        "title": "JR Product Engineer",
        "desc": "Análisis de datos de producción y demand planning. "
                "Reportes de KPI y business analyst. Supply chain coordination.",
        "expected_area": "Estrategia",
        "expected_seniority": "Junior",
    },
    {
        "title": "Analista JR de Travel Management",
        "desc": "Administración de viajes corporativos. Gestión de proveedores "
                "y reporting de gastos de viaje. Negociación comercial.",
        "expected_area": "Comercial",
        "expected_seniority": "Junior",
    },
]


# ── score_job ──────────────────────────────────────────────────────────────

class TestScoreJob:
    def test_finance_analyst_scores_high(self):
        score = score_job("JR Finance Analyst", "control de gestión finanzas fp&a")
        assert score >= 70

    def test_operario_scores_near_zero(self):
        score = score_job("Operario de planta", "operario mecánico soldador")
        assert score <= 10

    def test_baseline_is_30_for_unknown(self):
        score = score_job("Posición desconocida XYZ", "")
        assert score == 30

    def test_clamp_at_100(self):
        all_kw = " ".join(
            k for k in [
                "control de gestión", "fp&a", "finanzas", "pricing",
                "treasury", "estrategia", "business analyst",
            ]
        )
        score = score_job("Super Analyst", all_kw)
        assert score == 100

    def test_clamp_at_0(self):
        score = score_job(
            "mecánico soldador tornero chapista",
            "operario técnico de planta electricista",
        )
        assert score == 0

    @pytest.mark.parametrize("job", REAL_JOBS, ids=[j["title"] for j in REAL_JOBS])
    def test_real_toyota_jobs_score_above_baseline(self, job):
        score = score_job(job["title"], job["desc"])
        assert score > 30, f"{job['title']} should score above baseline"


# ── detect_area ────────────────────────────────────────────────────────────

class TestDetectArea:
    @pytest.mark.parametrize("job", REAL_JOBS, ids=[j["title"] for j in REAL_JOBS])
    def test_real_toyota_areas(self, job):
        area = detect_area(job["title"], job["desc"])
        assert area == job["expected_area"]

    def test_finanzas_keywords(self):
        for kw in ["controller", "fp&a", "treasury", "tesorería", "auditoría"]:
            assert detect_area(kw) == "Finanzas", f"'{kw}' should map to Finanzas"

    def test_comercial_keywords(self):
        for kw in ["pricing", "ventas", "trade marketing"]:
            assert detect_area(kw) == "Comercial", f"'{kw}' should map to Comercial"

    def test_no_area_for_generic_title(self):
        assert detect_area("Coordinador General") is None

    def test_it_area(self):
        assert detect_area("Data Engineer", "software developer sistemas") == "IT"

    def test_rrhh_area(self):
        assert detect_area("Talent Acquisition Specialist", "recursos humanos") == "RRHH"


# ── detect_seniority ──────────────────────────────────────────────────────

class TestDetectSeniority:
    @pytest.mark.parametrize("job", REAL_JOBS, ids=[j["title"] for j in REAL_JOBS])
    def test_real_toyota_seniority(self, job):
        seniority = detect_seniority(job["title"], job["desc"])
        assert seniority == job["expected_seniority"]

    def test_trainee(self):
        assert detect_seniority("Young Professional Program") == "Trainee"

    def test_lead(self):
        assert detect_seniority("Gerente de Finanzas") == "Lead"

    def test_senior(self):
        assert detect_seniority("Senior Analyst") == "Senior"

    def test_ssr(self):
        assert detect_seniority("Analista Semi Senior") == "SSr"

    def test_no_seniority(self):
        assert detect_seniority("Coordinador de Proyectos") is None


# ── enrich_all (integration) ──────────────────────────────────────────────

class TestEnrichAll:
    def test_enriches_all_rows(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY, company TEXT NOT NULL, title TEXT NOT NULL,
                location TEXT, country TEXT, posted_on TEXT, url TEXT, area TEXT,
                seniority TEXT, score INTEGER, raw_description TEXT,
                scraped_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("t-1", "Test", "JR Finance Analyst", "Zarate", "Argentina", "", "",
             None, None, None, "control de gestión finanzas", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("t-2", "Test", "Operario mecánico", "Zarate", "Argentina", "", "",
             None, None, None, "soldador tornero", "2026-01-01"),
        )
        conn.commit()
        conn.close()

        n = enrich_all(db_path)
        assert n == 2

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT id, score, area, seniority FROM jobs ORDER BY id"
        ).fetchall()
        conn.close()

        # Finance analyst
        assert rows[0][1] >= 60
        assert rows[0][2] == "Finanzas"
        assert rows[0][3] == "Junior"

        # Operario
        assert rows[1][1] <= 10
        assert rows[1][2] is None

    def test_raises_if_no_db(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            enrich_all(tmp_path / "nonexistent.db")
