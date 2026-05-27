"""
Calcula score (0-100) de match entre cada vacante y el perfil objetivo:
  - Egresado en Admin de Empresas (UdeSA) + cursando Master en Finanzas
  - Áreas de interés: finanzas, control de gestión, comercial, estrategia, planning
También detecta área principal y seniority a partir del título.
"""
import sqlite3
from pathlib import Path

from db import DB_PATH

POSITIVE_KEYWORDS: dict[str, int] = {
    # Finanzas core
    "control de gestión": 25,
    "controller": 25,
    "fp&a": 25,
    "financial planning": 25,
    "financial analyst": 25,
    "financial controller": 25,
    "planeamiento financiero": 22,
    "finanzas": 20,
    "finance": 20,
    "accounting": 18,
    "contabilidad": 18,
    "treasury": 18,
    "tesorería": 18,
    "auditor": 18,
    "auditoría": 15,
    "internal audit": 18,
    "tax": 15,
    "compliance": 14,
    "risk management": 14,
    "controlling": 20,
    "cost analyst": 20,
    "budget": 16,
    "forecast": 16,
    # Comercial / estrategia
    "pricing": 20,
    "business analyst": 20,
    "estrategia": 18,
    "strategy": 18,
    "business intelligence": 16,
    "comercial": 16,
    "commercial": 16,
    "sales analyst": 16,
    "revenue": 15,
    "análisis de datos": 15,
    "data analyst": 15,
    "planning": 14,
    "reporting": 14,
    "marketing": 14,
    "trade marketing": 13,
    "demand planning": 15,
    "supply chain": 12,
    # Entry-level
    "trainee": 13,
    "young professional": 13,
    "jóvenes profesionales": 13,
    "internship": 11,
    "working student": 10,
    "apprentice": 8,
    # General admin/business
    "administración": 11,
    "ventas": 11,
    "kpi": 10,
    "procurement": 12,
    "purchasing": 12,
    "project manager": 10,
    "program manager": 10,
    "consultant": 10,
}

NEGATIVE_KEYWORDS: dict[str, int] = {
    # Español
    "mecánico": -60,
    "soldador": -60,
    "tornero": -60,
    "chapista": -60,
    "lavador": -60,
    "operario": -50,
    "operador produção": -50,
    "técnico de planta": -45,
    "electricista": -45,
    "pintor": -45,
    "chofer": -45,
    "vigilancia": -45,
    "limpieza": -40,
    # Inglés
    "mechanic": -55,
    "welder": -55,
    "machinist": -55,
    "machine repair": -50,
    "skilled trade": -50,
    "technician": -35,
    "assembly": -40,
    "operator": -35,
    "hgv driver": -45,
    "janitor": -45,
    "custodian": -45,
    # Alemán
    "mechatroniker": -50,
    "ausbildung": -30,
    "monteur": -45,
    "kfz techniker": -50,
    "lagerlogistik": -40,
    # Portugués
    "operador produção multifuncional": -55,
    "técnico de manutenção": -40,
    "almacenista": -40,
}

AREA_RULES: list[tuple[str, list[str]]] = [
    ("Finanzas", [
        "control de gestión", "controller", "controlling", "fp&a", "finanzas", "finance",
        "treasury", "tesorería", "tax", "auditoría", "contable", "accounting",
        "accountant", "financial analyst", "financial planning", "auditor",
        "internal audit", "budget", "cost analyst", "bookkeep", "contabilidad",
        "risk management", "risikomanagement", "compliance", "actuary",
        "underwriting", "finanzen", "comptab",
    ]),
    ("Comercial", [
        "comercial", "commercial", "ventas", "sales", "pricing", "trade marketing",
        "marketing", "ejecutivo de cuentas", "key account", "account manager",
        "brand manager", "product marketing", "customer success",
        "business development", "head of brand", "recouvrement",
        "conseiller clientèle", "kundenberat",
    ]),
    ("Estrategia", [
        "estrategia", "strategy", "business analyst", "planning", "consulting",
        "consultant", "business intelligence", "data analyst", "analyst",
        "project manager", "program manager", "chef de projet",
        "projektmanager", "demand planning", "planner",
    ]),
    ("Operaciones", [
        "operations", "supply chain", "supply", "demand", "logística", "logistics",
        "abastecimiento", "manufactura", "manufacturing", "production",
        "quality", "calidad", "procurement", "purchasing", "warehouse",
        "almacén", "plant manager", "lean", "continuous improvement",
        "environmental engineer", "safety", "maintenance",
        "lagerlogistik", "approvisionnement",
    ]),
    ("RRHH", [
        "recursos humanos", "rrhh", "talent", "human resources", "people",
        "recruitment", "recruiter", "employer branding", "hr ", "hr-",
        "ressources humaines", "personalwesen", "trainer", "learning",
        "compensation", "benefits", "payroll",
    ]),
    ("IT", [
        "sistemas", "developer", "data engineer", "data scientist", "software",
        "devops", "cloud", "architect", "frontend", "backend", "full stack",
        "fullstack", "machine learning", "android", "ios ", "cybersecurity",
        "security specialist", "informatique", "entwickler", "infotainment",
        "sap ", "platform engineer", "robotics",
    ]),
    ("Ingeniería", [
        "engineer", "engineering", "ingénieur", "ingeniero", "calibration",
        "powertrain", "vehicle", "chassis", "electrical engineer",
        "mechanical engineer", "design engineer", "product engineer",
        "launch engineer", "test engineer", "validation",
    ]),
    ("Legal", [
        "legal", "lawyer", "abogado", "counsel", "compliance officer",
        "governance", "jurídico", "juridique",
    ]),
    ("Comunicación", [
        "comunicación", "communication", "corporate affairs", "prensa",
        "press", "public relations", "internal comms",
    ]),
]

SENIORITY_RULES: list[tuple[str, list[str]]] = [
    ("Trainee", [
        "trainee", "young professional", "jóvenes profesionales",
        "pasante", "internship", "intern ", "becario", "apprentice",
        "working student", "werkstudent", "aprendiz", "ausbildung",
        "alternance", "stagiaire", "estagiário", "estágio",
    ]),
    ("Lead", [
        "lead ", "manager", "gerente", "jefe", "head of", "director",
        "directeur", "leiter", "supervisor",
        "superintendent", "chef de",
        "group manager", "team leader", "principal",
    ]),
    ("SSr", ["semi senior", "ssr", "semi sr"]),
    ("Senior", [
        "senior", " sr.", " sr ", "(sr)", "staff ", "expert",
        "especialista sr", "spécialiste senior",
    ]),
    ("Junior", [
        "junior", " jr.", " jr ", "(jr)", "jr ", "analista jr",
        "entry level", "entry-level", "niveau débutant",
    ]),
]


def score_job(title: str, description: str = "") -> int:
    """Score 0-100. Baseline 30, suma positivos, resta negativos, clamp."""
    text = f"{title} {description}".lower()
    score = 30
    for kw, w in POSITIVE_KEYWORDS.items():
        if kw in text:
            score += w
    for kw, w in NEGATIVE_KEYWORDS.items():
        if kw in text:
            score += w
    return max(0, min(100, score))


def detect_area(title: str, description: str = "") -> str | None:
    text = f"{title} {description}".lower()
    for area, kws in AREA_RULES:
        if any(kw in text for kw in kws):
            return area
    return None


def detect_seniority(title: str, description: str = "") -> str | None:
    text = f"{title} {description}".lower()
    for level, kws in SENIORITY_RULES:
        if any(kw in text for kw in kws):
            return level
    return None


def enrich_all(db_path: Path = DB_PATH) -> int:
    """Aplica scoring + clasificación a todas las vacantes."""
    if not db_path.exists():
        raise FileNotFoundError(f"No existe {db_path}. Corré scraper_toyota.py primero.")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT id, title, raw_description FROM jobs").fetchall()
    for job_id, title, desc in rows:
        desc = desc or ""
        cur.execute(
            "UPDATE jobs SET score = ?, area = ?, seniority = ? WHERE id = ?",
            (score_job(title, desc), detect_area(title, desc),
             detect_seniority(title, desc), job_id),
        )
    conn.commit()
    conn.close()
    return len(rows)


def main() -> None:
    print("Calculando scores y clasificando area/seniority...")
    n = enrich_all()
    print(f"  -> {n} vacantes enriquecidas")


if __name__ == "__main__":
    main()
