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


# ── Header ─────────────────────────────────────────────────────────────────
st.title("🚗 AutoJobs — Vacantes Automotriz")

last_updated = get_last_updated()
if last_updated:
    st.caption(f"Vacantes globales de automotrices · Última actualización: **{last_updated}**")
else:
    st.caption("Vacantes globales de automotrices | Filtrá por empresa, país, área, seniority y más")

# ── Sidebar: filtros ────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

# Toggle activas/todas
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

# Búsqueda libre
search_text = st.sidebar.text_input(
    "Buscar en título",
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

# ── Filtrado ────────────────────────────────────────────────────────────────
mask = (
    df["company"].isin(selected_companies)
    & (df["score"].fillna(0) >= min_score)
)

# Búsqueda libre en título
if search_text.strip():
    mask = mask & df["title"].str.contains(search_text.strip(), case=False, na=False)

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
c1.metric("Vacantes", len(filtered))
c2.metric("Empresas", filtered["company"].nunique())
if "country" in filtered.columns:
    c3.metric("Países", filtered["country"].nunique())
else:
    c3.metric("Países", "—")
c4.metric("Match (score ≥ 70)", int((filtered["score"].fillna(0) >= 70).sum()))
avg = filtered["score"].mean()
c5.metric("Score promedio", f"{avg:.0f}" if pd.notna(avg) else "—")

st.divider()

# ── Gráficos ────────────────────────────────────────────────────────────────
g1, g2, g3 = st.columns(3)
with g1:
    st.subheader("Por empresa")
    if len(filtered):
        by_company = filtered.groupby("company").size().sort_values(ascending=False)
        st.bar_chart(by_company)
    else:
        st.info("Sin datos")

with g2:
    st.subheader("Por país (top 10)")
    if len(filtered) and "country" in filtered.columns and filtered["country"].notna().any():
        by_country = filtered.groupby("country").size().sort_values(ascending=False).head(10)
        st.bar_chart(by_country)
    else:
        st.info("Sin datos de país")

with g3:
    st.subheader("Por área")
    if len(filtered) and filtered["area"].notna().any():
        by_area = filtered.groupby("area").size().sort_values(ascending=False)
        st.bar_chart(by_area)
    else:
        st.info("Sin áreas detectadas")

st.divider()

# ── Tabla + Exportar CSV ───────────────────────────────────────────────────
col_header, col_export = st.columns([3, 1])
with col_header:
    st.subheader(f"Vacantes ({len(filtered)} de {len(df)} totales)")
with col_export:
    display_cols = ["company", "title", "country", "location", "area", "seniority", "posted_on", "score", "url"]
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
    height=600,
)
