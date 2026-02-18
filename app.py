import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests

st.set_page_config(page_title="Climat en France", layout="wide")

VARIABLES = {
    "temperature_2m_mean": "Température moyenne (°C)",
    "nb_days_heatwave": "Jours de canicule",
    "nb_days_snow": "Jours de neige",
}

COLORSCALES = {
    "temperature_2m_mean": "RdBu_r",
    "nb_days_heatwave": "RdBu_r",
    "nb_days_snow": "RdBu",
}


@st.cache_data
def load_data():
    df = pd.read_csv("data/all_prefectures_1950_2025_yearly.csv")
    df["Departement"] = df["Departement"].astype(str).str.strip()
    df["dept_code"] = df["Departement"].apply(normalize_dept_code)
    return df


@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def normalize_dept_code(code):
    code = str(code).strip()
    if code in ("2A", "2B", "2a", "2b"):
        return code.upper()
    try:
        return f"{int(code):02d}"
    except ValueError:
        return code


def compute_period_means(df_pref, variable):
    sorted_df = df_pref.sort_values("year").dropna(subset=[variable])
    first_20 = sorted_df.head(20)
    last_20 = sorted_df.tail(20)
    mean_first = first_20[variable].mean()
    mean_last = last_20[variable].mean()
    years_first = (int(first_20["year"].min()), int(first_20["year"].max()))
    years_last = (int(last_20["year"].min()), int(last_20["year"].max()))
    return mean_first, mean_last, years_first, years_last


def compute_map_data(df, variable, relative=False):
    records = []
    for commune, group in df.groupby("Commune"):
        dept_code = group["dept_code"].iloc[0]
        dept_raw = group["Departement"].iloc[0]
        sorted_g = group.sort_values("year").dropna(subset=[variable])
        if len(sorted_g) < 2:
            continue
        first_20 = sorted_g.head(20)
        last_20 = sorted_g.tail(20)
        mean_first = first_20[variable].mean()
        mean_last = last_20[variable].mean()
        if relative:
            gap = ((mean_last - mean_first) / mean_first * 100) if mean_first != 0 else float("nan")
        else:
            gap = mean_last - mean_first
        records.append({
            "Commune": commune,
            "dept_code": dept_code,
            "Departement": dept_raw,
            "gap": gap,
        })
    return pd.DataFrame(records)


# ── Load data ──────────────────────────────────────────────────────────────────
df = load_data()

try:
    geojson = load_geojson()
    map_available = True
except Exception:
    map_available = False

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Climat en France — Analyse par Préfecture")
st.markdown("Données issues de l'archive [Open-Meteo](https://open-meteo.com/), 1950–2025.")

# ── Selectors ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    prefectures = sorted(df["Commune"].unique())
    prefecture = st.selectbox("Préfecture", prefectures)
with col2:
    variable = st.selectbox(
        "Variable",
        list(VARIABLES.keys()),
        format_func=lambda k: VARIABLES[k],
    )

label = VARIABLES[variable]

# ── Filter prefecture data ──────────────────────────────────────────────────────
df_pref = df[df["Commune"] == prefecture].sort_values("year").dropna(subset=[variable])

if df_pref.empty:
    st.warning("Pas de données pour cette préfecture et cette variable.")
    st.stop()

mean_first, mean_last, years_first, years_last = compute_period_means(df_pref, variable)
gap = mean_last - mean_first

# ── Time series ────────────────────────────────────────────────────────────────
st.subheader(f"Série temporelle — {prefecture}")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_pref["year"],
    y=df_pref[variable],
    mode="lines+markers",
    name=label,
    line=dict(color="#1f77b4", width=2),
    marker=dict(size=5),
    hovertemplate="%{x} : %{y:.2f}<extra></extra>",
))

fig.add_hline(
    y=mean_first,
    line_dash="dash",
    line_color="steelblue",
    annotation_text=f"Moy. {years_first[0]}–{years_first[1]} : {mean_first:.2f}",
    annotation_position="top left",
)
fig.add_hline(
    y=mean_last,
    line_dash="dot",
    line_color="firebrick",
    annotation_text=f"Moy. {years_last[0]}–{years_last[1]} : {mean_last:.2f}",
    annotation_position="bottom right",
)

fig.update_layout(
    xaxis_title="Année",
    yaxis_title=label,
    hovermode="x unified",
    height=420,
    margin=dict(l=40, r=40, t=20, b=40),
    legend=dict(orientation="h", y=1.02),
)

st.plotly_chart(fig, use_container_width=True)

# ── Year cursor ─────────────────────────────────────────────────────────────────
years_available = sorted(df_pref["year"].unique())
selected_year = st.slider(
    "Année sélectionnée",
    min_value=int(years_available[0]),
    max_value=int(years_available[-1]),
    value=int(years_available[-1]),
)

row = df_pref[df_pref["year"] == selected_year]
if not row.empty:
    val = row[variable].values[0]
    st.metric(label=f"{label} en {selected_year}", value=f"{val:.2f}")
else:
    st.info(f"Pas de donnée pour {selected_year}.")

# ── Period statistics ───────────────────────────────────────────────────────────
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric(
    label=f"Moyenne {years_first[0]}–{years_first[1]}",
    value=f"{mean_first:.2f}",
)
c2.metric(
    label=f"Moyenne {years_last[0]}–{years_last[1]}",
    value=f"{mean_last:.2f}",
)
delta_str = f"+{gap:.2f}" if gap >= 0 else f"{gap:.2f}"
c3.metric(
    label="Écart (dernière − première période)",
    value=delta_str,
    delta=delta_str,
)

# ── Choropleth map ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader(f"Carte de France — Écart entre les deux périodes ({label})")

if not map_available:
    st.error("Impossible de charger le GeoJSON (vérifiez votre connexion internet).")
else:
    use_relative = variable == "nb_days_snow"
    map_df = compute_map_data(df, variable, relative=use_relative)

    abs_max = map_df["gap"].abs().max()

    gap_label = "Écart relatif (%)" if use_relative else "Écart"
    hover_fmt = ":.1f" if use_relative else ":.2f"

    fig_map = px.choropleth(
        map_df,
        geojson=geojson,
        locations="dept_code",
        featureidkey="properties.code",
        color="gap",
        color_continuous_scale=COLORSCALES[variable],
        range_color=(-abs_max, abs_max),
        hover_name="Commune",
        hover_data={
            "dept_code": True,
            "gap": hover_fmt,
        },
        labels={"gap": gap_label, "dept_code": "Département"},
    )

    fig_map.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator",
    )

    colorbar_title = f"Δ {label} (%)" if use_relative else f"Δ {label}"
    tickfmt = ".0f" if use_relative else ".1f"

    fig_map.update_layout(
        height=550,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_colorbar=dict(
            title=colorbar_title,
            tickformat=tickfmt,
        ),
    )

    st.plotly_chart(fig_map, use_container_width=True)

    if use_relative:
        st.caption(
            f"Écart relatif (%) = (moyenne {years_last[0]}–{years_last[1]} − moyenne {years_first[0]}–{years_first[1]}) "
            f"/ moyenne {years_first[0]}–{years_first[1]} × 100, "
            "calculé pour chaque préfecture sur ses 20 premières et 20 dernières années de données disponibles."
        )
    else:
        st.caption(
            f"Écart = moyenne des {years_last[0]}–{years_last[1]} moins moyenne des {years_first[0]}–{years_first[1]}, "
            "calculé pour chaque préfecture sur ses 20 premières et 20 dernières années de données disponibles."
        )
