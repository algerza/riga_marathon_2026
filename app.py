import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Analysing trends on Rimi Riga Marathon event",
    page_icon="🏃",
    layout="wide",
)

PALETTE_BLUE  = "#b52f29"   # crimson — primary / men
PALETTE_PINK  = "#e8735a"   # coral — women
PALETTE_DARK  = "#2d3748"   # dark slate — accents, Latvia, Elite
CAT_ORDER     = ["Elite", "Amateur Pro", "Amateur", "Occasional"]
CAT_COLORS    = {"Elite": "#2d3748", "Amateur Pro": "#b52f29", "Amateur": "#e8a87c", "Occasional": "#eeeeee"}
GENDER_COLORS = {"Men": PALETTE_BLUE, "Women": PALETTE_PINK}
DIST_ORDER    = ["Marathon", "Half Marathon", "10Km", "Dpd Mile"]

# ── helpers ───────────────────────────────────────────────────────────────────
def time_to_seconds(t):
    if pd.isna(t) or not t:
        return None
    try:
        h, m, s = map(float, str(t).split(":"))
        return h * 3600 + m * 60 + s
    except:
        return None

def seconds_to_hms(s):
    if pd.isna(s): return ""
    h = int(s // 3600); m = int((s % 3600) // 60); sec = int(s % 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def seconds_to_hm(s):
    if pd.isna(s): return ""
    h = int(s // 3600); m = int((s % 3600) // 60)
    return f"{h}:{m:02d}"

def fmt_hover_seconds(series):
    return series.apply(seconds_to_hms)

def add_performance_category(df):
    df["performance_category"] = "Occasional"
    standards = {
        "Marathon":      {"men": {"elite": 9000,  "amateur_pro": 10800, "amateur": 14400}, "women": {"elite": 10800, "amateur_pro": 12600, "amateur": 15600}, "age_penalty": 300},
        "Half Marathon": {"men": {"elite": 4500,  "amateur_pro": 5400,  "amateur": 7200},  "women": {"elite": 5400,  "amateur_pro": 6300,  "amateur": 7800},  "age_penalty": 150},
        "10Km":          {"men": {"elite": 2100,  "amateur_pro": 2700,  "amateur": 3600},  "women": {"elite": 2400,  "amateur_pro": 3000,  "amateur": 3900},  "age_penalty": 60},
        "Dpd Mile":      {"men": {"elite": 270,   "amateur_pro": 360,   "amateur": 480},   "women": {"elite": 330,   "amateur_pro": 420,   "amateur": 540},   "age_penalty": 10},
    }
    for idx, row in df.iterrows():
        rt, t, g, ag = row["race_type"], row["seconds"], str(row["gender"]).lower(), str(row["age_group"])
        if rt not in standards or pd.isna(t): continue
        try: age_start = int(ag.split()[-1].split("-")[0])
        except: age_start = 30
        gk  = "men" if "m" in g else "women"
        std = standards[rt][gk]
        pen = standards[rt]["age_penalty"]
        ap  = ((age_start - 30) // 5) * pen if age_start >= 35 else 0
        if   t <= std["elite"]       + ap: df.at[idx, "performance_category"] = "Elite"
        elif t <= std["amateur_pro"] + ap: df.at[idx, "performance_category"] = "Amateur Pro"
        elif t <= std["amateur"]     + ap: df.at[idx, "performance_category"] = "Amateur"
    return df

@st.cache_data
def load_data():
    df = pd.read_csv("riga_complete_dataset_hashed.csv")
    duplicates = df.groupby(["event_id", "full_name"]).size().loc[lambda x: x > 1].index
    dup_mask = df.set_index(["event_id", "full_name"]).index.isin(duplicates)
    n_dup_rows = int(dup_mask.sum())
    n_dup_athletes = len(duplicates)
    df = df[~dup_mask]
    df["seconds"] = df["finish_netto"].apply(time_to_seconds)
    df["hours"]   = df["seconds"] / 3600
    df = add_performance_category(df)
    return df, n_dup_rows, n_dup_athletes

df, N_DUP_ROWS, N_DUP_ATHLETES = load_data()
YEARS = sorted(df["year"].unique())

# ── page header ───────────────────────────────────────────────────────────────
st.image("hero_image.jpg", use_column_width=True)
# st.title("🏃 From Start to Stats")
# st.subtitle("Analysing Rimi Riga marathon event over time")


dff = df.copy()

# ── Dashboard overview ────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stHorizontalBlock"] > div {
    background: #ffffff;
    border: none;
    border-radius: 0;
    padding: 0px;
    box-shadow: none;
}
</style>
""", unsafe_allow_html=True)

def _kpi_fig(kpi_value, kpi_label, traces, yaxis_extra=None, height=300):
    fig = go.Figure()
    for t in (traces if isinstance(traces, list) else [traces]):
        fig.add_trace(t)
    fig.add_annotation(
        text=kpi_label,
        xref="paper", yref="paper", x=0.0, y=1.48,
        showarrow=False, xanchor="left",
        font=dict(size=14, color="#888888"),
    )
    fig.add_annotation(
        text=f"<b>{kpi_value}</b>",
        xref="paper", yref="paper", x=0.0, y=1.28,
        showarrow=False, xanchor="left",
        font=dict(size=38, color="#1a1a1a"),
    )
    yaxis = dict(showgrid=False, zeroline=False, showticklabels=False, title="")
    if yaxis_extra:
        yaxis.update(yaxis_extra)
    fig.update_layout(
        height=height,
        margin=dict(t=120, b=20, l=8, r=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=12, color="#aaaaaa"), title=""),
        yaxis=yaxis,
        showlegend=False,
    )
    return fig

athletes_per_year  = dff.groupby("year")["name"].nunique().reset_index(name="athletes")
countries_per_year = dff.groupby("year")["country"].nunique().reset_index(name="countries")

gender_pct_year = (
    dff.groupby(["year", "gender"])["name"].nunique()
    .reset_index(name="athletes")
)
gender_pivot = gender_pct_year.pivot_table(index="year", columns="gender", values="athletes", fill_value=0).reset_index()
gender_pivot["pct_women"] = gender_pivot["Women"] / (gender_pivot["Men"] + gender_pivot["Women"]) * 100
gender_pivot["pct_men"]   = 100 - gender_pivot["pct_women"]
overall_pct_women = round(dff[dff["gender"] == "Women"]["name"].nunique() / dff["name"].nunique() * 100, 1)

ov1, ov2, ov3 = st.columns(3)

with ov1:
    fig = _kpi_fig(
        kpi_value=f"{dff['name'].nunique():,}",
        kpi_label="Unique athletes (all time)",
        traces=go.Bar(
            x=athletes_per_year["year"].astype(str),
            y=athletes_per_year["athletes"],
            marker_color=PALETTE_BLUE, opacity=0.75,
            hovertemplate="%{x}: %{y:,}<extra></extra>",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

with ov2:
    fig = _kpi_fig(
        kpi_value=str(dff["country"].nunique()),
        kpi_label="Distinct countries (all time)",
        traces=go.Scatter(
            x=countries_per_year["year"].astype(str),
            y=countries_per_year["countries"],
            mode="lines+markers",
            fill="tozeroy",
            fillcolor="rgba(181,47,41,0.12)",
            line=dict(color=PALETTE_BLUE, width=2),
            marker=dict(size=5, color=PALETTE_BLUE),
            hovertemplate="%{x}: %{y} countries<extra></extra>",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

with ov3:
    fig = _kpi_fig(
        kpi_value=f"{overall_pct_women}% Women",
        kpi_label="Gender split (all time)",
        traces=[
            go.Scatter(
                x=gender_pivot["year"].astype(str),
                y=gender_pivot["pct_women"],
                name="Women", mode="lines+markers",
                line=dict(color=PALETTE_PINK, width=2),
                marker=dict(size=5, color=PALETTE_PINK),
                hovertemplate="%{x} Women: %{y:.1f}%<extra></extra>",
            ),
            go.Scatter(
                x=gender_pivot["year"].astype(str),
                y=gender_pivot["pct_men"],
                name="Men", mode="lines+markers",
                line=dict(color=PALETTE_BLUE, width=2),
                marker=dict(size=5, color=PALETTE_BLUE),
                hovertemplate="%{x} Men: %{y:.1f}%<extra></extra>",
            ),
        ],
    )
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.15, x=0, font=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)


st.markdown(f"""
Every May, the streets of Riga fill with runners. The Rimi Riga Marathon is one of the
Baltic's biggest mass-participation events — but behind the finisher medals and the cheering
crowds lies a dataset that tells a richer story.

This analysis covers **{df['name'].nunique():,} unique finishers** from
**{df['country'].nunique()} countries** who competed between **{YEARS[0]} and {YEARS[-1]}**
across four distances: Marathon, Half Marathon, 10 km, and the Depo Mile.
What follows is a data-driven portrait of the race — how it has grown, who is showing up,
where they come from, how fast they run, and whether they ever come back.

Some things you might expect: Latvians dominate the start line.
Men used to outnumber women, but tha trend is changing over time, becoming more even distribution. Younger runners are... not necessarily faster.
Other things are more surprising. The competitive layer — Elite and Amateur Pro athletes —
is quietly expanding. Year-to-year loyalty is low but the runners who do return form a
disproportionately loyal core. And the age group that posts the fastest median marathon
time is probably not the one you'd guess.
""")    

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 1 · GROWTH
# ═══════════════════════════════════════════════════════════════════════════════
st.header("The race is growing")
st.markdown(
    "The charts below are based on **finishers** recorded in the results dataset, not total registrations. "
    "That said, the growth trend is consistent with official figures published by Rimi Riga Marathon: "
    "a more than doubling of the field in the last three years. "
    "Finisher counts track this trajectory closely, confirming the dataset captures the race's rapid expansion."
)

totals    = dff.groupby("year")["name"].nunique().reset_index(name="athletes")
by_gender = dff.groupby(["year", "gender"])["name"].nunique().reset_index(name="athletes")

col_a, col_b = st.columns(2)

with col_a:
    fig = px.bar(
        totals, x=totals["year"].astype(str), y="athletes",
        text="athletes",
        labels={"x": "Year", "athletes": "Athletes"},
        title="Total unique athletes per year",
        color_discrete_sequence=[PALETTE_BLUE],
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(showlegend=False, yaxis_title="Athletes", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    fig = px.line(
        by_gender, x="year", y="athletes", color="gender",
        markers=True, text="athletes",
        color_discrete_map=GENDER_COLORS,
        labels={"athletes": "Athletes", "year": "Year", "gender": ""},
        title="Athletes by gender per year",
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(xaxis=dict(tickvals=YEARS))
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 2 · INTERNATIONAL
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.header("The world is coming to Riga")

country_totals = dff.groupby("country")["name"].nunique().reset_index(name="total")
top_foreign    = country_totals[country_totals["country"] != "LAT"].nlargest(8, "total")["country"].tolist()
top_countries  = ["LAT"] + top_foreign

by_cy = dff.groupby(["year", "country"])["name"].nunique().reset_index(name="athletes")
by_cy["country_group"] = by_cy["country"].apply(lambda c: c if c in top_countries else "Other")
pivot_c = by_cy.groupby(["year", "country_group"])["athletes"].sum().reset_index()
pivot_c = pivot_c.pivot_table(index="year", columns="country_group", values="athletes", fill_value=0)
col_order = ["LAT"] + [c for c in top_foreign if c in pivot_c.columns] + (["Other"] if "Other" in pivot_c.columns else [])
pivot_c   = pivot_c.reindex(columns=col_order).reset_index()
pivot_pct = pivot_c.copy()
row_tots  = pivot_pct[col_order].sum(axis=1)
for c in col_order:
    pivot_pct[c] = pivot_pct[c] / row_tots * 100

long_pct = pivot_pct.melt(id_vars="year", value_vars=col_order, var_name="Country", value_name="Share")

_country_scale = [
    "#e8c4b8",  # light blush
    "#e8a87c",  # warm sand (Amateur tone)
    "#e8735a",  # coral (PALETTE_PINK)
    "#c94f3a",  # mid crimson
    "#b52f29",  # crimson (PALETTE_BLUE)
    "#8c2020",  # deep crimson
    "#5c1a1a",  # very dark crimson
    "#2d3748",  # dark slate (Other)
]
country_palette = (
    {col_order[0]: PALETTE_DARK} |
    dict(zip(col_order[1:], _country_scale[:len(col_order)-1]))
)

# ── section 2 insights ────────────────────────────────────────────────────────
_first_year, _last_year = YEARS[0], YEARS[-1]
_lat_share_first = pivot_pct.loc[pivot_pct["year"] == _first_year, "LAT"].values[0]
_lat_share_last  = pivot_pct.loc[pivot_pct["year"] == _last_year,  "LAT"].values[0]
_foreign_first   = dff[dff["year"] == _first_year]["country"].nunique() - 1
_foreign_last    = dff[dff["year"] == _last_year]["country"].nunique() - 1
_top1, _top2     = top_foreign[0], top_foreign[1]

st.markdown(
    f"Latvia has always dominated the start line, but its share has fallen from "
    f"**{_lat_share_first:.0f}%** in {_first_year} to **{_lat_share_last:.0f}%** in {_last_year} "
    f"as the event attracts more international runners. The number of foreign countries represented "
    f"grew from **{_foreign_first}** to **{_foreign_last}** over the same period. "
    f"Among non-Latvian nations, **Germany** and **Great Britain** consistently send the most athletes, "
    f"reflecting strong running cultures in the wider Baltic and Northern European region."
)

col_intl_a, col_intl_b = st.columns(2)

with col_intl_a:
    fig = px.bar(
        long_pct, x=long_pct["year"].astype(str), y="Share", color="Country",
        color_discrete_map=country_palette,
        labels={"x": "Year", "Share": "Share (%)"},
        title="Share of athletes by country",
        text=long_pct["Share"].apply(lambda v: f"{v:.1f}%" if v > 3 else ""),
        barmode="stack",
    )
    fig.update_traces(textposition="inside")
    fig.update_layout(yaxis_ticksuffix="%", xaxis_title="", legend_title="Country")
    st.plotly_chart(fig, use_container_width=True)

with col_intl_b:
    country_totals_growth = (
        dff[dff["country"] != "LAT"]
        .groupby("country")["name"].nunique()
        .reset_index(name="total_athletes")
        .nlargest(5, "total_athletes")
        .sort_values("total_athletes", ascending=False)
    )
    fig_growth = px.bar(
        country_totals_growth,
        x="total_athletes", y="country",
        orientation="h",
        text="total_athletes",
        color="country",
        color_discrete_map=country_palette,
        labels={"country": "", "total_athletes": "Total runners"},
        title="Top 5 countries by total runners (excl. Latvia)",
    )
    fig_growth.update_traces(textposition="outside", texttemplate="%{text:,}")
    fig_growth.update_layout(xaxis_title="Total runners", showlegend=False)
    st.plotly_chart(fig_growth, use_container_width=True)

# ── LV vs non-LV performance category composition ────────────────────────────
dff["origin"] = dff["country"].apply(lambda c: "Latvian" if c == "LAT" else "Non-Latvian")


# ═══════════════════════════════════════════════════════════════════════════════
# 3 · PERFORMANCE CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.header("Who is running? The field is broadening")
st.markdown(
    "As the race grows it pulls in more first-time and recreational runners, so the **Occasional** category "
    "is gaining share — a natural consequence of a mass-participation event scaling up. "
    "But the picture changes significantly depending on which distance you look at."
)
st.markdown(
    "**Distance shapes the competitive mix.** The shorter the race, the more recreational the field: "
    "10 km and the Dpd Mile are dominated by Occasional runners, while Marathon and Half Marathon attract "
    "a noticeably higher share of structured athletes. "
    "For **men**, the Amateur and Amateur Pro breakdown is broadly similar across Marathon and Half Marathon — "
    "both distances draw a comparable proportion of serious club runners. "
    "For **women**, the pattern is more striking: competitiveness increases with distance. "
    "The Marathon is clearly the most competitive distance for women, with the highest combined share of "
    "Amateur and Amateur Pro finishers — suggesting that women who commit to the full distance tend to train more seriously for it."
)
st.markdown(
    "In order to set a general athlete classification, I assigned each finisher to a category based on finish time, gender, and age group:\n\n"
    "- **Elite** — sub-2:30 men / sub-3:00 women (marathon equivalent), adjusted upward by ~5 min per 5-year age band above 35\n"
    "- **Amateur Pro** — sub-3:00 men / sub-3:30 women; serious club runners who train consistently\n"
    "- **Amateur** — sub-4:00 men / sub-4:20 women; recreational runners with a structured programme\n"
    "- **Occasional** — everyone else; the largest share of the field across all distances\n\n"
    "Thresholds scale proportionally across Half Marathon, 10 km, and the Dpd Mile. "
    "Use the distance selector and **Men / Women** tabs below to explore."
)

st.markdown("""
<style>
div[data-testid="stTabs"] button {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    padding: 10px 40px !important;
}
div[data-testid="stTabs"] {
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

dist_avail = [d for d in DIST_ORDER if d in dff["race_type"].unique()]
sel_dist = st.radio("Select distance", dist_avail, horizontal=True, key="cat_dist")

genders_in = [g for g in ["Men", "Women"] if g in dff["gender"].unique()]
tabs = st.tabs(genders_in)

for tab, gender in zip(tabs, genders_in):
    with tab:
        da = (
            dff[(dff["gender"] == gender) & (dff["race_type"] == sel_dist)]
            .groupby(["year", "performance_category"])["name"].nunique()
            .reset_index(name="athletes")
        )
        pivot = da.pivot_table(index="year", columns="performance_category", values="athletes", fill_value=0)
        pivot = pivot.reindex(columns=[c for c in CAT_ORDER if c in pivot.columns])
        pivot_pct = pivot.div(pivot.sum(axis=1), axis=0).mul(100).reset_index()
        long = pivot_pct.melt(id_vars="year", var_name="Level", value_name="Share")
        long["text"] = long["Share"].apply(lambda v: f"{v:.0f}%" if v > 5 else "")

        fig = px.bar(
            long, x=long["year"].astype(str), y="Share", color="Level",
            color_discrete_map=CAT_COLORS,
            category_orders={"Level": CAT_ORDER},
            text="text", barmode="stack",
            labels={"x": "Year", "Share": "Share (%)"},
            title=f"{gender} · {sel_dist} — distribution by performance level",
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(yaxis_ticksuffix="%", xaxis_title="", legend_title="Level")
        st.plotly_chart(fig, use_container_width=True)

sel_origin_dist = st.radio("Select distance", dist_avail, horizontal=True, key="origin_dist")
genders_origin = [g for g in ["Men", "Women"] if g in dff["gender"].unique()]
tabs_origin = st.tabs(genders_origin)

for _tab, _gender in zip(tabs_origin, genders_origin):
    with _tab:
        _filtered = dff[(dff["race_type"] == sel_origin_dist) & (dff["gender"] == _gender)]
        _cat_f = _filtered.groupby(["year", "origin", "performance_category"]).size().reset_index(name="n")
        _cat_tot_f = _filtered.groupby(["year", "origin"]).size().reset_index(name="total")
        _cat_f = _cat_f.merge(_cat_tot_f, on=["year", "origin"])
        _cat_f["pct"] = _cat_f["n"] / _cat_f["total"] * 100

        _oc = _filtered.groupby(["origin", "performance_category"]).size().reset_index(name="n")
        _ot = _filtered.groupby("origin").size().reset_index(name="total")
        _oc = _oc.merge(_ot, on="origin")
        _oc["pct"] = _oc["n"] / _oc["total"] * 100

        def _pct_f(origin, cat):
            row = _oc[(_oc["origin"] == origin) & (_oc["performance_category"] == cat)]
            return round(row["pct"].values[0], 1) if len(row) else 0.0

        _lv_occ  = _pct_f("Latvian",     "Occasional")
        _nlv_occ = _pct_f("Non-Latvian", "Occasional")
        _lv_ep   = round(_pct_f("Latvian",     "Elite") + _pct_f("Latvian",     "Amateur Pro"), 1)
        _nlv_ep  = round(_pct_f("Non-Latvian", "Elite") + _pct_f("Non-Latvian", "Amateur Pro"), 1)
        _lv_am   = _pct_f("Latvian",     "Amateur")
        _nlv_am  = _pct_f("Non-Latvian", "Amateur")

        st.caption(f"Stats below reflect **{_gender.lower()}** finishers in the **{sel_origin_dist}**. Change the distance or gender tab to update.")

        st.markdown(
            f"Runners who travel to Riga from abroad are a self-selected, more competitive cohort. "
            f"**{_nlv_occ:.0f}%** of non-Latvian finishers fall into the Occasional category, "
            f"compared to **{_lv_occ:.0f}%** of Latvians — a gap of {abs(_lv_occ - _nlv_occ):.0f} percentage points. "
            f"At the top end, Elite and Amateur Pro runners make up **{_nlv_ep:.0f}%** of non-Latvian starters "
            f"versus just **{_lv_ep:.0f}%** of Latvians. "
            f"The Amateur tier — structured recreational runners with a proper training plan — "
            f"tells the same story: **{_nlv_am:.0f}%** non-Latvian versus **{_lv_am:.0f}%** Latvian. "
            f"This pattern holds consistently across every year in the dataset: the international field is not "
            f"simply getting larger in terms of number of runners - it is meaningfully more trained. Making the trip to race abroad is, in itself, "
            f"a signal of commitment."
        )

        fig_origin = make_subplots(
            cols=2,
            subplot_titles=["Latvian runners", "Non-Latvian runners"],
            shared_yaxes=True,
        )
        for _col_i, _origin in enumerate(["Latvian", "Non-Latvian"], start=1):
            _sub = _cat_f[_cat_f["origin"] == _origin]
            for _cat in reversed(CAT_ORDER):
                _cs = _sub[_sub["performance_category"] == _cat]
                fig_origin.add_trace(
                    go.Bar(
                        x=_cs["year"].astype(str),
                        y=_cs["pct"],
                        name=_cat,
                        marker_color=CAT_COLORS[_cat],
                        legendgroup=_cat,
                        showlegend=(_col_i == 1),
                        hovertemplate=f"{_cat}: %{{y:.1f}}%<extra></extra>",
                    ),
                    row=1, col=_col_i,
                )
        fig_origin.update_layout(
            barmode="stack",
            height=380,
            margin=dict(t=60, b=20),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.12, x=0),
            legend_title_text="",
        )
        fig_origin.update_yaxes(ticksuffix="%", showgrid=False)
        fig_origin.update_xaxes(showgrid=False)
        fig_origin.update_traces(texttemplate="%{y:.0f}%", textposition="inside")
        st.plotly_chart(fig_origin, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 4 · PERCENTILE BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.header("Where would you finish?")
st.markdown(
    "Ever wondered how your finish time stacks up against the rest of the field? "
    "This chart shows the finish time you would need to land in the top 1%, 5%, 10%, 25%, or 50% of all finishers "
    "for a given distance — calculated across all editions in the dataset combined."
)
st.markdown(
    "A few things stand out. The gap between men and women narrows at slower percentiles: "
    "elite men and women are far apart, but by the median the difference is much smaller in relative terms. "
    "The top 1% times are a useful reality check — they reflect genuinely elite-level performances, "
    "while the top 50% (the median) is the most meaningful benchmark for a recreational runner "
    "trying to gauge where a solid training block would place them. What is your predicted finish time by your smartwatch?"
)

df_v       = dff[dff["seconds"].notna() & (dff["seconds"] > 0)].copy()
races_avail = [d for d in DIST_ORDER if d in df_v["race_type"].unique()]
sel_race   = st.radio("Distance", races_avail, horizontal=True, key="pct_race")

pct_vals   = [1, 5, 10, 25, 50]
pct_labels = ["Top 1%", "Top 5%", "Top 10%", "Top 25%", "Top 50%"]

rdata = df_v[df_v["race_type"] == sel_race]
rows  = []
for gender in ["Men", "Women"]:
    gdata = rdata[rdata["gender"] == gender]["seconds"]
    if len(gdata) < 10: continue
    for pv, pl in zip(pct_vals, pct_labels):
        secs = float(np.percentile(gdata, pv))
        rows.append({"Gender": gender, "Percentile": pl, "seconds": secs,
                     "hours": secs / 3600, "label": seconds_to_hms(secs), "n": len(gdata)})

if rows:
    pct_df = pd.DataFrame(rows)
    fig = px.bar(
        pct_df, x="Percentile", y="hours", color="Gender", barmode="group",
        color_discrete_map=GENDER_COLORS,
        text="label",
        custom_data=["label", "n"],
        category_orders={"Percentile": pct_labels},
        labels={"hours": "Finish time (h)", "Percentile": ""},
        title=f"{sel_race} — finish time benchmarks (all selected years combined)",
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{customdata[0]}<br>n=%{customdata[1]:,}<extra></extra>",
    )
    fig.update_layout(
        yaxis=dict(tickformat=".1f", title="Finish time (h)"),
        legend_title="Gender",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough data for the current selection.")

# ═══════════════════════════════════════════════════════════════════════════════
# 5 · AGE & PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.header("The sweet spot: which age group runs fastest?")
st.markdown(
    "Athletics research consistently shows that endurance performance peaks in the **late 20s to mid-30s**, "
    "and crucially, the longer the distance, the more that peak can be sustained into the 40s. "
    "Sprint and short-distance speed does favour younger athletes — VO2max and fast-twitch capacity peak early — "
    "but marathon and half-marathon performance depends far more on aerobic efficiency, pacing discipline, and accumulated training volume, "
    "all of which improve with age and experience. Studies of mass-participation marathon fields (Lepers & Cattagni, Leyk et al.) "
    "consistently find the fastest median ages in the 30–44 range, with a more gradual decline than shorter events."
)
st.markdown(
    "This dataset reflects that pattern. For the **Marathon and Half Marathon**, the 30s age groups tend to dominate, "
    "and performance holds up well into the early 40s before declining. For **10 km and the Dpd Mile**, "
    "the advantage shifts slightly younger, consistent with the greater contribution of speed and VO2max at shorter distances. "
    "There is also a selection effect at play: 20-somethings in a mass-participation event skew heavily recreational, "
    "whereas the 35–44 cohort contains the highest concentration of structured, experienced runners. "
    "The **whiskers** show the 25th–75th percentile range — wider bars signal a more diverse field, "
    "narrower bars a more homogeneous and typically more competitive age group."
)

def age_sort_key(ag):
    try: return int(str(ag).split()[-1].split("-")[0])
    except: return 99

df_age      = df_v[df_v["age_group"].notna()].copy()
races_age   = [d for d in DIST_ORDER if d in df_age["race_type"].unique()]
sel_race_age = st.radio("Distance", races_age, horizontal=True, key="age_race")

rdata = df_age[df_age["race_type"] == sel_race_age]
genders_age = [g for g in ["Men", "Women"] if g in rdata["gender"].unique()]
tabs2 = st.tabs(genders_age)

for tab, gender in zip(tabs2, genders_age):
    with tab:
        gdata = rdata[rdata["gender"] == gender]
        age_stats = gdata.groupby("age_group")["seconds"].agg(
            median="median",
            p25=lambda x: np.percentile(x, 25),
            p75=lambda x: np.percentile(x, 75),
            count="count",
        ).reset_index()
        age_stats = age_stats[age_stats["count"] >= 10].copy()
        age_stats["sort_key"] = age_stats["age_group"].apply(age_sort_key)
        age_stats = age_stats.sort_values("sort_key").reset_index(drop=True)
        age_stats["ag_short"] = age_stats["age_group"].str.replace(
            r"^(Men|Women|M|F|V|S)\s", "", regex=True)
        age_stats["median_hm"]  = age_stats["median"].apply(seconds_to_hm)
        age_stats["p25_hm"]     = age_stats["p25"].apply(seconds_to_hm)
        age_stats["p75_hm"]     = age_stats["p75"].apply(seconds_to_hm)
        age_stats["median_h"]   = age_stats["median"] / 3600
        age_stats["p25_h"]      = age_stats["p25"] / 3600
        age_stats["p75_h"]      = age_stats["p75"] / 3600

        if age_stats.empty:
            st.info("Not enough data.")
            continue

        best_idx = age_stats["median_h"].idxmin()
        age_stats["color"] = [GENDER_COLORS[gender]] * len(age_stats)
        age_stats.at[best_idx, "color"] = "#ffd600"

        fig = go.Figure()

        for _, row in age_stats.iterrows():
            is_best = row.name == best_idx
            fig.add_trace(go.Bar(
                x=[row["ag_short"]], y=[row["median_h"]],
                marker_color=row["color"],
                opacity=1.0 if is_best else 0.65,
                name="Fastest" if is_best else "Other",
                showlegend=is_best,
                customdata=[[row["median_hm"], row["p25_hm"], row["p75_hm"], int(row["count"])]],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Median: %{customdata[0]}<br>"
                    "P25–P75: %{customdata[1]} – %{customdata[2]}<br>"
                    "n=%{customdata[3]:,}<extra></extra>"
                ),
            ))
            fig.add_trace(go.Scatter(
                x=[row["ag_short"], row["ag_short"]],
                y=[row["p25_h"], row["p75_h"]],
                mode="lines",
                line=dict(color="#333333", width=2),
                showlegend=False,
                hoverinfo="skip",
            ))

        best_ag   = age_stats.loc[best_idx, "ag_short"]
        best_time = age_stats.loc[best_idx, "median_hm"]
        fig.add_annotation(
            text=f"Fastest: {best_ag} — median {best_time}",
            xref="paper", yref="paper", x=0.5, y=1.05,
            showarrow=False, font=dict(size=12),
            bgcolor="#fff9c4", borderpad=4,
        )
        fig.update_layout(
            title=f"{gender} — {sel_race_age} median finish time by age group",
            xaxis_title="Age group", yaxis_title="Median finish time (h)",
            barmode="overlay", showlegend=False,
            yaxis=dict(tickformat=".2f"),
        )
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 6 · RETENTION
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.header("Loyalty: who comes back?")

athlete_years = df.groupby("full_name").agg(
    num_years=("year", lambda x: x.nunique()),
    num_distances=("race_type", lambda x: x.nunique()),
).reset_index()
total = len(athlete_years)

one_time   = int((athlete_years["num_years"] == 1).sum())
multi_year = int((athlete_years["num_years"] >  1).sum())
loyal      = int((athlete_years["num_years"] >= 3).sum())
multi_dist = int((athlete_years["num_distances"] > 1).sum())

all_years = sorted(df["year"].unique())
ret_rows  = []
for i in range(len(all_years) - 1):
    y1, y2 = all_years[i], all_years[i+1]
    if y1 == 2021 or y2 == 2021: continue
    s1, s2 = set(df[df["year"] == y1]["full_name"]), set(df[df["year"] == y2]["full_name"])
    ret_rows.append({"Transition": f"{y1}→{y2}", "Retention %": len(s1 & s2) / len(s1) * 100})
ret_df  = pd.DataFrame(ret_rows)
avg_ret = ret_df["Retention %"].mean()

st.markdown(f"""
The majority of Riga Marathon finishers — **{one_time/total*100:.0f}%** — cross the finish line once
and never return. Yet the **{multi_year:,} athletes** ({multi_year/total*100:.0f}%) who come back for
a second edition form the race's most committed community. Of those, **{loyal:,}** have shown up in
three or more different years — a loyal core that keeps the event's character consistent even as
thousands of first-timers cycle through each edition.

Year-to-year retention averages **{avg_ret:.1f}%**: for every 100 runners who finish in one year,
roughly {avg_ret:.0f} will line up again the following year. The 2021 edition is excluded from
this calculation — pandemic-driven restrictions made that year's participation patterns incomparable
to the rest of the series. Retention measures only consecutive-year pairs: an athlete who ran
in 2022 and 2025 (skipping 2023–2024) would not appear as retained in any single transition,
but is included in the multi-year totals.

Beyond loyalty across years, **{multi_dist/total*100:.0f}% of returning athletes** have competed in
more than one distance format — a sign they use the event to push themselves beyond their comfort zone.
""")

with st.expander("Methodology note"):
    st.markdown(f"""
    **Athlete identity:** Each participant is identified by their full name as it appears in the
    official results. This works well in practice but can misattribute results if two different
    people share a name, or undercount loyalty if an athlete's name changes between editions.

    **Duplicate removal:** Before any analysis, rows where the same full name appears more than
    once in the same event are removed entirely. If a name has two results for the same event,
    both entries are dropped to avoid ambiguity about which result is correct.
    In this dataset, this affected **{N_DUP_ATHLETES:,} athlete–event combinations**
    ({N_DUP_ROWS:,} rows removed in total).

    **Retention rate:** Defined as the share of year-one finishers whose name also appears among
    year-two finishers. Only consecutive year-pairs are evaluated. Non-consecutive gaps
    (e.g. 2022 → 2025) are not tracked in the year-to-year chart but are captured in the
    "participated in 2+ years" totals.
    """)

loyalty_colors = ["#f5c6c4", "#e8735a", "#b52f29", "#7a1a16", "#3d0d0b"]

col_a, col_b = st.columns(2)

yd = athlete_years["num_years"].value_counts().sort_index().reset_index()
yd.columns = ["Years participated", "Athletes"]
yd["Share"] = (yd["Athletes"] / total * 100).round(1)
yd["label"] = yd["Share"].apply(lambda v: f"{v}%")

with col_a:
    fig = px.pie(
        yd,
        names=yd["Years participated"].astype(str),
        values="Athletes",
        color_discrete_sequence=loyalty_colors[:len(yd)],
        title="Most runners come once — a rare few keep returning",
    )
    fig.update_traces(texttemplate="%{label} yr: %{percent}", textposition="inside")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    fig = px.bar(
        ret_df, x="Transition", y="Retention %",
        text=ret_df["Retention %"].apply(lambda v: f"{v:.1f}%"),
        color_discrete_sequence=[PALETTE_BLUE],
        title=f"Year-to-year retention — avg {avg_ret:.1f}% (2021 excluded)",
    )
    fig.add_hline(y=avg_ret, line_dash="dash", line_color=PALETTE_DARK,
                  annotation_text=f"Avg {avg_ret:.1f}%", annotation_position="top right")
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_range=[0, 50], xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.info(
    "**Watch this space — the four-year medal cycle.** "
    "Starting in 2025, Rimi Riga Marathon is introducing a collectible medal programme spanning four consecutive editions. "
    "Runners who complete the same distance across four years unlock a special commemorative medal. "
    "This is a direct retention lever, and it will be fascinating to see whether year-to-year return rates climb as a result — "
    "particularly in the 2026 and 2027 editions when the first cohort of collectors will be mid-cycle. "
    "Read more: [Launching a four-year medal cycle](https://rimirigamarathon.com/en/news/launching-a-four-year-medal-cycle-collect-your-riga/)"
)

cross = (
    athlete_years.groupby(["num_years", "num_distances"])
    .size().reset_index(name="n")
)
cross_pivot = cross.pivot_table(index="num_years", columns="num_distances", values="n", fill_value=0)
cross_pct   = cross_pivot.div(cross_pivot.sum(axis=1), axis=0).mul(100).reset_index()
dist_cols   = [c for c in cross_pct.columns if c != "num_years"]
cross_long  = cross_pct.melt(id_vars="num_years", value_vars=dist_cols,
                              var_name="Distances tried", value_name="Share")
cross_long["text"] = cross_long["Share"].apply(lambda v: f"{v:.0f}%" if v > 6 else "")
cross_long["Distances tried"] = cross_long["Distances tried"].astype(str)

# ── cross-tab insights ────────────────────────────────────────────────────────
_one_yr_one_dist  = cross_pct.loc[cross_pct["num_years"] == 1, 1].values
_one_yr_one_dist  = float(_one_yr_one_dist[0]) if len(_one_yr_one_dist) else 0
_max_yr           = int(cross_pct["num_years"].max())
_max_yr_multi     = float(cross_pct.loc[cross_pct["num_years"] == _max_yr,
                          [c for c in dist_cols if c > 1]].sum(axis=1).values[0]) if _max_yr > 1 else 0
_single_dist_only = int((athlete_years["num_distances"] == 1).sum())
_multi_dist_pct   = round((athlete_years["num_distances"] > 1).sum() / total * 100, 1)

st.markdown(
    f"The chart below reveals a strong link between commitment and curiosity. "
    f"Among athletes who raced only once, **{_one_yr_one_dist:.0f}%** stuck to a single distance — "
    f"most likely picking one event and never returning. "
    f"But as the number of editions climbs, the picture changes dramatically: "
    f"athletes who have participated in **{_max_yr} different years** have almost all tried more than one distance, "
    f"with **{_max_yr_multi:.0f}%** having explored multiple formats. "
    f"Across the whole dataset, **{_multi_dist_pct}%** of all athletes have raced at least two different distances — "
    f"a sign that the event's variety is one of its strongest retention tools. "
    f"Runners don't just come back; they use each return to challenge themselves in a new way."
)

fig = px.bar(
    cross_long,
    x=cross_long["num_years"].astype(str), y="Share",
    color="Distances tried",
    color_discrete_sequence=loyalty_colors[:len(dist_cols)],
    barmode="stack", text="text",
    labels={"num_years": "Years participated", "Share": "Share (%)"},
    title="More editions = more distances explored",
    category_orders={"Distances tried": [str(c) for c in sorted(dist_cols)]},
)
fig.update_traces(textposition="inside")
fig.update_layout(
    yaxis_ticksuffix="%", xaxis_title="Years participated",
    legend_title="Distances tried",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown(
    "The Rimi Riga Marathon is more than a race — it is a growing, internationalising, multi-generational community. "
    "It has doubled its field in three years, welcomed runners from over a hundred countries, and built a loyal core "
    "that keeps returning edition after edition. The data tells a story of a city event that has found its moment: "
    "recreational enough to welcome anyone, competitive enough to challenge the serious, and large enough that the "
    "numbers now have real things to say.\n\n"
    "If you found this analysis interesting or have questions, feel free to connect on "
    "[LinkedIn](https://www.linkedin.com/in/alvaroager/)."
)
