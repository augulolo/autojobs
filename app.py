"""
Dashboard Streamlit para visualizar vacantes automotriz.
Correr: streamlit run app.py
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path("data/jobs.db")

st.set_page_config(
    page_title="AutoJobs — Vacantes Automotriz",
    page_icon="🚗",
    layout="wide",
)

# ── Logos por empresa (URLs públicas) ─────────────────────────────────────
COMPANY_LOGOS: dict[str, str] = {
    "Toyota": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Toyota.svg/200px-Toyota.svg.png",
    "Renault": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Renault_2021_Text.svg/200px-Renault_2021_Text.svg.png",
    "Nissan": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Nissan_2020_logo.svg/200px-Nissan_2020_logo.svg.png",
    "Ford": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Ford_Motor_Company_Logo.svg/200px-Ford_Motor_Company_Logo.svg.png",
    "Honda": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Honda.svg/200px-Honda.svg.png",
    "VW Group": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Volkswagen_logo_2019.svg/200px-Volkswagen_logo_2019.svg.png",
    "Scania": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Scania_logo.svg/200px-Scania_logo.svg.png",
    "Stellantis": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Stellantis_logo.svg/200px-Stellantis_logo.svg.png",
}

COMPANY_CAREERS: dict[str, str] = {
    "Toyota": "https://toyota.wd5.myworkdayjobs.com/TLAC",
    "Renault": "https://alliancewd.wd3.myworkdayjobs.com/renault-group-careers",
    "Nissan": "https://alliance.wd3.myworkdayjobs.com/nissanjobs",
    "Ford": "https://efds.fa.em5.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1",
    "Honda": "https://hondamotorargentina.hiringroom.com/jobs",
    "VW Group": "https://jobs.volkswagen-group.com",
    "Scania": "https://jobs.scania.com",
    "Stellantis": "https://stellantis.empregare.com/pt-br/vagas",
}

AREA_ICONS: dict[str, str] = {
    "Finanzas": "💰",
    "Comercial": "🤝",
    "Estrategia": "🎯",
    "IT": "💻",
    "RRHH": "👥",
    "Operaciones": "⚙️",
    "Ingeniería": "🔧",
    "Legal": "⚖️",
    "Comunicación": "📢",
}

SENIORITY_ORDER = ["Trainee", "Junior", "SSr", "Senior", "Lead"]


# ── Data loading ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_jobs(active_only: bool = True) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    where = "WHERE is_active = 1" if active_only else ""
    df = pd.read_sql_query(
        f"SELECT * FROM jobs {where} ORDER BY score DESC NULLS LAST, posted_on DESC",
        conn,
    )
    conn.close()
    return df


@st.cache_data(ttl=300)
def get_last_updated() -> str | None:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT MAX(scraped_at) FROM jobs").fetchone()
    conn.close()
    if row and row[0]:
        try:
            dt = datetime.fromisoformat(row[0])
            return dt.strftime("%d/%m/%Y %H:%M UTC")
        except ValueError:
            return row[0][:19]
    return None


# ── Custom CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Company cards */
    .company-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    }
    .company-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(255, 107, 53, 0.15);
    }
    .company-card img {
        height: 40px;
        object-fit: contain;
        margin-bottom: 0.5rem;
        filter: brightness(0) invert(1);
    }
    .company-card .name {
        font-weight: 600;
        font-size: 1rem;
        color: #fafafa;
        margin-bottom: 0.3rem;
    }
    .company-card .stat {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FF6B35;
    }
    .company-card .label {
        font-size: 0.75rem;
        color: #888;
        margin-top: -0.3rem;
    }
    .company-card a {
        display: inline-block;
        margin-top: 0.5rem;
        color: #FF6B35;
        text-decoration: none;
        font-size: 0.8rem;
    }

    /* Top match card */
    .match-card {
        background: linear-gradient(135deg, #1a2e1a 0%, #162e16 100%);
        border: 1px solid #2a4a2a;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .match-card .score-badge {
        background: #FF6B35;
        color: white;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.85rem;
        display: inline-block;
    }
    .match-card .title {
        font-weight: 600;
        font-size: 1rem;
        color: #fafafa;
        margin: 0.4rem 0 0.2rem 0;
    }
    .match-card .meta {
        font-size: 0.8rem;
        color: #aaa;
    }

    /* Section headers */
    .section-icon {
        font-size: 1.3rem;
        margin-right: 0.3rem;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────
st.title("🚗 AutoJobs — Vacantes Automotriz")

last_updated = get_last_updated()
if last_updated:
    st.caption(
        f"Vacantes globales del sector automotriz · "
        f"Actualización automática diaria · Última: **{last_updated}**"
    )
else:
    st.caption("Vacantes globales de automotrices | Filtrá por empresa, país, área, seniority y más")


# ── Sidebar: filtros ────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

show_inactive = st.sidebar.checkbox("Incluir vacantes inactivas", value=False)
df = load_jobs(active_only=not show_inactive)

if df.empty:
    st.warning(
        "No hay vacantes cargadas todavía.\n\n"
        "Corré en la terminal:\n"
        "```bash\npython run_all.py\n```\n"
        "y después refrescá esta página."
    )
    st.stop()

# Búsqueda libre (título + descripción)
search_text = st.sidebar.text_input(
    "Buscar en título y descripción",
    placeholder="Ej: finance, analista, engineer...",
)

# Empresa
companies = sorted(df["company"].dropna().unique().tolist())
selected_companies = st.sidebar.multiselect("Empresa", companies, default=companies)

# País
if "country" in df.columns:
    countries_raw = df["country"].dropna().unique().tolist()
    countries = sorted(countries_raw)
    selected_countries = st.sidebar.multiselect("País", countries, default=countries)
else:
    selected_countries = None

# Área
areas_available = sorted(df["area"].dropna().unique().tolist())
selected_areas = st.sidebar.multiselect("Área", areas_available, default=areas_available)
include_no_area = st.sidebar.checkbox("Incluir vacantes sin área detectada", value=True)

# Seniority
sen_available = sorted(df["seniority"].dropna().unique().tolist())
selected_sen = st.sidebar.multiselect("Seniority", sen_available, default=sen_available)
include_no_sen = st.sidebar.checkbox("Incluir vacantes sin seniority detectado", value=True)

# Score
min_score = st.sidebar.slider("Score mínimo", 0, 100, 0, step=5)

st.sidebar.divider()
st.sidebar.caption("Datos actualizados automáticamente cada día a las 08:00 ART vía GitHub Actions.")

# ── Filtrado ────────────────────────────────────────────────────────────────
mask = (
    df["company"].isin(selected_companies)
    & (df["score"].fillna(0) >= min_score)
)

# Búsqueda libre en título + descripción
if search_text.strip():
    q = search_text.strip()
    title_match = df["title"].str.contains(q, case=False, na=False)
    desc_match = df["raw_description"].str.contains(q, case=False, na=False) if "raw_description" in df.columns else False
    mask = mask & (title_match | desc_match)

# País
if selected_countries is not None and "country" in df.columns:
    mask = mask & df["country"].isin(selected_countries)

# Área
area_mask = df["area"].isin(selected_areas)
if include_no_area:
    area_mask = area_mask | df["area"].isna()

# Seniority
sen_mask = df["seniority"].isin(selected_sen)
if include_no_sen:
    sen_mask = sen_mask | df["seniority"].isna()

filtered = df[mask & area_mask & sen_mask].copy()


# ── KPI cards ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Vacantes", f"{len(filtered):,}")
c2.metric("Empresas", filtered["company"].nunique())
if "country" in filtered.columns:
    c3.metric("Países", filtered["country"].nunique())
else:
    c3.metric("Países", "—")
high_match = int((filtered["score"].fillna(0) >= 70).sum())
c4.metric("Match ≥ 70", high_match)
avg = filtered["score"].mean()
c5.metric("Score promedio", f"{avg:.0f}" if pd.notna(avg) else "—")


# ── Tabs ────────────────────────────────────────────────────────────────────
tab_overview, tab_companies, tab_matches, tab_table = st.tabs([
    "📊 Resumen",
    "🏢 Empresas",
    "🎯 Top Matches",
    "📋 Todas las vacantes",
])


# ── TAB: Resumen ────────────────────────────────────────────────────────────
with tab_overview:
    st.divider()

    # Gráficos principales
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Vacantes por empresa")
        if len(filtered):
            by_company = filtered.groupby("company").size().sort_values(ascending=True)
            st.bar_chart(by_company, horizontal=True)
        else:
            st.info("Sin datos")

    with g2:
        st.subheader("Top 10 países")
        if len(filtered) and "country" in filtered.columns and filtered["country"].notna().any():
            by_country = filtered.groupby("country").size().sort_values(ascending=True).tail(10)
            st.bar_chart(by_country, horizontal=True)
        else:
            st.info("Sin datos de país")

    g3, g4 = st.columns(2)
    with g3:
        st.subheader("Por área funcional")
        if len(filtered) and filtered["area"].notna().any():
            by_area = filtered.groupby("area").size().sort_values(ascending=True)
            st.bar_chart(by_area, horizontal=True)
        else:
            st.info("Sin áreas detectadas")

    with g4:
        st.subheader("Por seniority")
        if len(filtered) and filtered["seniority"].notna().any():
            by_sen = filtered.groupby("seniority").size()
            # Reindex to desired order
            ordered = [s for s in SENIORITY_ORDER if s in by_sen.index]
            by_sen = by_sen.reindex(ordered)
            st.bar_chart(by_sen, horizontal=True)
        else:
            st.info("Sin seniority detectado")

    # Distribución de score
    st.divider()
    st.subheader("Distribución de score de matching")
    if len(filtered) and filtered["score"].notna().any():
        score_bins = pd.cut(
            filtered["score"].dropna(),
            bins=[0, 20, 40, 60, 80, 100],
            labels=["0-20 (Bajo)", "21-40", "41-60 (Medio)", "61-80", "81-100 (Alto)"],
        )
        score_dist = score_bins.value_counts().sort_index()
        st.bar_chart(score_dist)
        st.caption(
            "El score refleja qué tan bien matchea cada vacante con un perfil de "
            "administración + finanzas. Vacantes ≥70 son los mejores matches."
        )


# ── TAB: Empresas ───────────────────────────────────────────────────────────
with tab_companies:
    st.divider()
    st.markdown("Detalle por empresa con vacantes activas, países de presencia y áreas más demandadas.")
    st.write("")

    cols = st.columns(4)
    for idx, company in enumerate(sorted(filtered["company"].unique())):
        comp_df = filtered[filtered["company"] == company]
        n_jobs = len(comp_df)
        n_countries = comp_df["country"].nunique() if "country" in comp_df.columns else 0
        top_area = comp_df["area"].mode().iloc[0] if comp_df["area"].notna().any() else "—"
        top_area_icon = AREA_ICONS.get(top_area, "📌")
        avg_score = comp_df["score"].mean()
        logo_url = COMPANY_LOGOS.get(company, "")
        careers_url = COMPANY_CAREERS.get(company, "#")

        with cols[idx % 4]:
            logo_html = f'<img src="{logo_url}" alt="{company}">' if logo_url else ""
            st.markdown(f"""
            <div class="company-card">
                {logo_html}
                <div class="name">{company}</div>
                <div class="stat">{n_jobs}</div>
                <div class="label">vacantes activas</div>
                <div style="margin-top:0.6rem; font-size:0.82rem; color:#ccc;">
                    🌍 {n_countries} países · {top_area_icon} {top_area}<br>
                    📈 Score prom: <b>{avg_score:.0f}</b>
                </div>
                <a href="{careers_url}" target="_blank">Ver portal de careers →</a>
            </div>
            """, unsafe_allow_html=True)
            st.write("")  # spacer

    # Tabla comparativa
    st.divider()
    st.subheader("Comparativa de empresas")
    company_stats = []
    for company in sorted(filtered["company"].unique()):
        comp_df = filtered[filtered["company"] == company]
        company_stats.append({
            "Empresa": company,
            "Vacantes": len(comp_df),
            "Países": comp_df["country"].nunique() if "country" in comp_df.columns else 0,
            "Score prom": round(comp_df["score"].mean(), 1) if comp_df["score"].notna().any() else 0,
            "Match ≥70": int((comp_df["score"].fillna(0) >= 70).sum()),
            "Área top": comp_df["area"].mode().iloc[0] if comp_df["area"].notna().any() else "—",
        })
    stats_df = pd.DataFrame(company_stats).sort_values("Vacantes", ascending=False)
    st.dataframe(
        stats_df,
        column_config={
            "Score prom": st.column_config.ProgressColumn(
                "Score prom", min_value=0, max_value=100, format="%.0f"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )


# ── TAB: Top Matches ────────────────────────────────────────────────────────
with tab_matches:
    st.divider()
    st.markdown(
        "Las vacantes con **mayor score** para tu perfil de administración y finanzas. "
        "Hacé click en el link para postularte directo."
    )

    top_n = st.slider("Cantidad de top matches", 5, 50, 20, step=5)

    top_matches = filtered.nlargest(top_n, "score")

    if top_matches.empty:
        st.info("No hay vacantes con score calculado. Corré `python scoring.py` primero.")
    else:
        for _, row in top_matches.iterrows():
            score = int(row["score"]) if pd.notna(row["score"]) else 0
            company = row.get("company", "")
            title = row.get("title", "")
            country = row.get("country") if pd.notna(row.get("country")) else "—"
            area = row.get("area") if pd.notna(row.get("area")) else "—"
            seniority = row.get("seniority") if pd.notna(row.get("seniority")) else "—"
            url = row.get("url", "#")
            area_icon = AREA_ICONS.get(area, "📌") if area != "—" else "📌"

            # Color badge by score
            if score >= 80:
                badge_color = "#22c55e"  # green
            elif score >= 60:
                badge_color = "#FF6B35"  # orange
            else:
                badge_color = "#6b7280"  # gray

            logo_url = COMPANY_LOGOS.get(company, "")
            logo_html = f'<img src="{logo_url}" style="height:22px; filter:brightness(0) invert(1); vertical-align:middle; margin-right:6px;">' if logo_url else ""

            st.markdown(f"""
            <div class="match-card">
                <span class="score-badge" style="background:{badge_color};">{score}</span>
                <div class="title">{logo_html}{title}</div>
                <div class="meta">
                    {logo_html and "" or ""}{company} · 🌍 {country} · {area_icon} {area} · 🎓 {seniority}
                    · <a href="{url}" target="_blank" style="color:#FF6B35;">Postularme →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── TAB: Todas las vacantes ──────────────────────────────────────────────────
with tab_table:
    st.divider()

    col_header, col_export = st.columns([3, 1])
    with col_header:
        st.subheader(f"Vacantes ({len(filtered):,} de {len(df):,} totales)")
    with col_export:
        display_cols = [
            "company", "title", "country", "location", "area",
            "seniority", "posted_on", "score", "url",
        ]
        display_cols = [c for c in display_cols if c in filtered.columns]
        csv_data = filtered[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exportar CSV",
            data=csv_data,
            file_name="autojobs_vacantes.csv",
            mime="text/csv",
        )

    st.dataframe(
        filtered[display_cols],
        column_config={
            "company": "Empresa",
            "title": "Puesto",
            "country": "País",
            "location": "Ubicación",
            "area": "Área",
            "seniority": "Seniority",
            "posted_on": "Publicado",
            "score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%d"
            ),
            "url": st.column_config.LinkColumn("Postular", display_text="Ver →"),
        },
        hide_index=True,
        use_container_width=True,
        height=700,
    )


# ── Footer ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "AutoJobs — Scraping automático de 8 portales de careers del sector automotriz global. "
    "Datos actualizados diariamente a las 08:00 ART vía GitHub Actions. "
    "Score calculado vs perfil de administración + finanzas."
)
