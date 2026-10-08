"""Chart builders: data/<id>.csv -> Plotly figure -> HTML fragment (site) and PNGs (slides).

Every chart follows the dataviz method: the form is chosen by the data's job,
categorical hues are assigned in fixed slot order (never cycled), sequential
encodings use one hue, marks are thin, grids are hairlines, a legend is present
for two or more series, text uses text tokens, and every chart ships a table view
plus its CSV. Colors come from config.THEME (validated palette).
"""
from __future__ import annotations

import html
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme  # noqa: F401  (registers the templates)
from .config import CHARTS_OUT, DATA_OUT, FIG_OUT, THEME
from .countries import sort_key

PLOTLY_CONFIG = dict(
    responsive=True, displaylogo=False,
    modeBarButtonsToRemove=["select2d", "lasso2d", "autoScale2d", "zoomIn2d", "zoomOut2d"],
    toImageButtonOptions=dict(format="png", scale=2),
)
AGE_LABELS = [f"{a}-{a + 4}" for a in range(0, 80, 5)] + ["80+"]

CHARTS: dict[str, dict] = {}


def chart(cid: str, *, title: str, subtitle: str, source: str, note: str | None = None, height: int = 460,
          max_rows: int = 200):
    """Register a chart builder. The builder signature is fn(df, mode, t) -> go.Figure."""
    def deco(fn: Callable[[pd.DataFrame, str, dict], go.Figure]):
        CHARTS[cid] = dict(id=cid, title=title, subtitle=subtitle, source=source, note=note,
                           height=height, max_rows=max_rows, build=fn)
        return fn
    return deco


# ---- helpers ---------------------------------------------------------------------------------

def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def fmt_num(v: float) -> str:
    if pd.isna(v):
        return ""
    v = float(v)
    if abs(v) >= 1e9:
        return f"{v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.0f}k"
    return f"{v:.0f}"


def magnitude_axis(vmax: float) -> dict:
    """Clean ticks for a count axis (0, 2M, 4M ...)."""
    if vmax >= 4e6:
        step = 2e6 if vmax < 16e6 else 5e6
    elif vmax >= 1e6:
        step = 5e5
    elif vmax >= 2e5:
        step = 1e5
    elif vmax >= 5e4:
        step = 2.5e4
    else:
        step = 1e4
    ticks = [i * step for i in range(int(vmax // step) + 2)]
    return dict(tickvals=ticks, ticktext=[fmt_num(x) if x else "0" for x in ticks], range=[0, vmax])


def dumbbell(df: pd.DataFrame, cat: str, a: str, b: str, a_label: str, b_label: str, mode: str, t: dict,
             fmt=fmt_num, hover_a: str | None = None, hover_b: str | None = None, a_color: str | None = None,
             label_text: Callable | None = None) -> go.Figure:
    """Before -> after per item: one hue, two shades (dataviz form table)."""
    C = t["colorway"]
    a_color = a_color or t["earlier"]
    cats = df[cat].tolist()
    fig = go.Figure()
    for _, r in df.iterrows():
        if pd.notna(r[a]) and pd.notna(r[b]):
            fig.add_trace(go.Scatter(x=[r[a], r[b]], y=[r[cat], r[cat]], mode="lines",
                                     line=dict(color=t["baseline"], width=2), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=df[a], y=cats, mode="markers", name=a_label,
        marker=dict(color=a_color, size=10, line=dict(width=2, color=t["surface"])),
        hovertemplate=hover_a or f"<b>%{{y}}</b><br>{a_label}: %{{x:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=df[b], y=cats, mode="markers", name=b_label,
        marker=dict(color=C[0], size=11, line=dict(width=2, color=t["surface"])),
        hovertemplate=hover_b or f"<b>%{{y}}</b><br>{b_label}: %{{x:,.0f}}<extra></extra>"))
    # value label sits to the right of whichever marker is further out, so it never covers a dot
    labels = [label_text(v) if label_text else fmt(v) for v in df[b]]
    xmax = df[[a, b]].max(axis=1)
    # an invisible marker of the same size keeps Plotly's text offset, so the label clears the dot
    fig.add_trace(go.Scatter(x=xmax, y=cats, mode="markers+text", text=labels, textposition="middle right",
                             textfont=dict(color=t["text2"], size=11), cliponaxis=False,
                             marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(width=0)),
                             showlegend=False, hoverinfo="skip"))
    fig.update_yaxes(autorange="reversed", showgrid=True, gridcolor=t["grid"])
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"])
    return fig


# ---- 00 overview ------------------------------------------------------------------------------

@chart("ov_coverage_timeline",
       title="Time coverage of the sources in the ecosystem",
       subtitle="Years available per product, by section of this site",
       source="Project documentation of each source; see the source pages for details.", height=720, max_rows=40)
def ov_coverage_timeline(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    fams = list(dict.fromkeys(df.family))
    fig = go.Figure()
    for i, fam in enumerate(fams):
        d = df[df.family == fam]
        fig.add_trace(go.Bar(
            y=d["product"], x=d.end - d.start + 1, base=d.start, orientation="h", name=fam,
            marker=dict(color=C[i], cornerradius=4), width=0.62,
            customdata=d[["start", "end", "periodicity", "unit"]].values,
            hovertemplate="<b>%{y}</b><br>%{customdata[0]}–%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<extra></extra>"))
    fig.update_layout(barmode="overlay", bargap=0.3,
                      xaxis=dict(range=[1979, 2027.5], tickvals=[1980, 1990, 2000, 2010, 2020, 2026],
                                 showgrid=True, gridcolor=t["grid"], side="top"),
                      yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=11)),
                      legend=dict(y=-0.02, yanchor="top"), margin=dict(l=8, r=24, t=32, b=60))
    return fig


# ---- 01 United States -------------------------------------------------------------------------

@chart("us_stock_by_country",
       title="LAC-born population living in the United States, 2014 vs 2024",
       subtitle="Foreign-born residents by country of birth (naturalized citizens and non-citizens)",
       source="Census Bureau, ACS 1-year PUMS 2014 and 2024 (same records and weights as IPUMS USA); PWGTP-weighted.",
       note="Census 'foreign-born' excludes people born abroad to US-citizen parents, so counts run about 4% below IPUMS birthplace counts for Mexico.",
       height=640)
def us_stock_by_country(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    p = df.pivot(index="country", columns="year", values="population")[[2014, 2024]]
    p = p.sort_values(2024, ascending=False)
    top, rest = p.iloc[:18], p.iloc[18:]
    if len(rest):
        top.loc[f"Other LAC origins ({len(rest)} groups)"] = rest.sum()
    d = top.reset_index().rename(columns={2014: "y2014", 2024: "y2024"})
    d["change"] = d.y2024 / d.y2014 - 1
    fig = dumbbell(d, "country", "y2014", "y2024", "2014", "2024", mode, t,
                   hover_b="<b>%{y}</b><br>2024: %{x:,.0f}<br>change since 2014: %{customdata:+.0%}<extra></extra>")
    fig.data[-2].customdata = d.change
    fig.update_xaxes(**magnitude_axis(d[["y2014", "y2024"]].max().max() * 1.12), title_text="Persons")
    fig.update_layout(margin=dict(r=60))
    return fig


@chart("us_age_pyramid",
       title="Age structure of LAC-born residents in the United States, 2014 vs 2024",
       subtitle="Share of all LAC-born residents, by five-year age group and sex; 2014 drawn as an outline",
       source="Census Bureau, ACS 1-year PUMS 2014 and 2024; PWGTP-weighted. All LAC countries of birth.",
       height=520, max_rows=80)
def us_age_pyramid(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    fig = go.Figure()
    for year, outline in ((2024, False), (2014, True)):
        for sex, sign, col, show in (("Men", -1, C[0], True), ("Women", 1, C[1], True)):
            d = df[(df.year == year) & (df.sex == sex)].set_index("age_group").reindex(AGE_LABELS)
            kwargs = dict(
                x=sign * d.share_pct, y=AGE_LABELS, orientation="h", customdata=d.share_pct,
                hovertemplate=f"{sex}, {year}, %{{y}}: %{{customdata:.1f}}% of LAC-born<extra></extra>")
            if outline:
                fig.add_trace(go.Bar(name="2014 (outline)", legendgroup="2014", showlegend=(sex == "Men"),
                                     marker=dict(color="rgba(0,0,0,0)", line=dict(color=t["text2"], width=1.5)),
                                     **kwargs))
            else:
                fig.add_trace(go.Bar(name=f"{sex}, 2024", marker=dict(color=col, cornerradius=3), **kwargs))
    m = df.share_pct.max() * 1.15
    ticks = [v for v in (-8, -6, -4, -2, 0, 2, 4, 6, 8) if abs(v) <= m]
    fig.update_layout(barmode="overlay", bargap=0.18,
                      xaxis=dict(tickvals=ticks, ticktext=[f"{abs(v)}%" for v in ticks], range=[-m, m],
                                 showgrid=True, gridcolor=t["grid"], title_text="Share of LAC-born residents"),
                      yaxis=dict(categoryorder="array", categoryarray=AGE_LABELS, showgrid=False, title_text="Age"))
    fig.add_annotation(x=-m * 0.95, y=16, text="Men", showarrow=False, xanchor="left", font=dict(color=t["text2"]))
    fig.add_annotation(x=m * 0.95, y=16, text="Women", showarrow=False, xanchor="right", font=dict(color=t["text2"]))
    return fig


# ---- 02 Europe --------------------------------------------------------------------------------

@chart("eu_lac_born_2024",
       title="LAC-born residents in European reporting countries, 2024",
       subtitle="Top 12 countries of birth; bars split by the five largest host countries",
       source="Eurostat, migr_pop3ctb (population on 1 January by country of birth), 2024; EU, EFTA and candidate reporting countries.",
       note="France and Germany do not report this series, so their large LAC-born populations are missing here (see the citizenship and permit series for them).",
       height=520)
def eu_lac_born_2024(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    totals = df.groupby("country").population.sum().sort_values(ascending=False)
    keep = totals.index[:12].tolist()
    d = df[df.country.isin(keep)]
    hosts = d.groupby(["host", "host_name"]).population.sum().reset_index().sort_values("population", ascending=False)
    hosts = pd.concat([hosts[hosts.host != "OTHER"], hosts[hosts.host == "OTHER"]])
    fig = go.Figure()
    for i, (_, h) in enumerate(hosts.iterrows()):
        s = d[d.host == h.host].set_index("country").population.reindex(keep).fillna(0)
        color = t["other"] if h.host == "OTHER" else C[i]
        fig.add_trace(go.Bar(y=keep, x=s.values, orientation="h", name=h.host_name,
                             marker=dict(color=color, line=dict(color=t["surface"], width=1.5)),
                             hovertemplate=f"Born in %{{y}}, living in {h.host_name}: %{{x:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(x=totals[keep].values, y=keep, mode="text", text=[fmt_num(v) for v in totals[keep]],
                             textposition="middle right", textfont=dict(color=t["text2"], size=11),
                             showlegend=False, hoverinfo="skip", cliponaxis=False))
    fig.update_layout(barmode="stack", bargap=0.35,
                      xaxis=dict(**magnitude_axis(totals[keep].max() * 1.12), showgrid=True, gridcolor=t["grid"],
                                 title_text="Persons"),
                      yaxis=dict(autorange="reversed", showgrid=False), margin=dict(r=60))
    return fig


@chart("eu_first_permits_reason",
       title="First residence permits issued to LAC citizens in Europe, by reason, 2010–2025",
       subtitle="Permits issued in the year, all validity lengths, summed over reporting countries",
       source="Eurostat, migr_resfirst, citizens of 33 LAC countries; EU, EFTA and candidate reporting countries.",
       note="A permit is not a person, and the set of reporting countries grows over time (Germany reports from 2019). Use fixed country panels for trends.",
       height=460)
def eu_first_permits_reason(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    order = ["Employment", "Family", "Education", "Other reasons"]
    p = df.pivot(index="year", columns="reason", values="permits").reindex(columns=order).fillna(0)
    fig = go.Figure()
    for i, reason in enumerate(order):
        fig.add_trace(go.Bar(x=p.index, y=p[reason], name=reason,
                             marker=dict(color=C[i], line=dict(color=t["surface"], width=1.5), cornerradius=3),
                             hovertemplate="%{y:,.0f}<extra>" + reason + "</extra>"))
    totals = p.sum(axis=1)
    for y in (2010, 2015, 2019, 2022, 2025):
        if y in totals.index:
            fig.add_annotation(x=y, y=totals[y], text=fmt_num(totals[y]), showarrow=False, yshift=10,
                               font=dict(color=t["text2"], size=11))
    fig.update_layout(barmode="stack", bargap=0.3, hovermode="x unified",
                      xaxis=dict(dtick=1, tickangle=0, tickfont=dict(size=11)),
                      yaxis=dict(**magnitude_axis(totals.max() * 1.1), title_text="Permits"))
    return fig


@chart("eu_asylum_first_time",
       title="First-time asylum applicants from LAC countries in Europe, 2008–2025",
       subtitle="Five largest citizenships in 2025 and the rest of the region",
       source="Eurostat, migr_asyappctza (first-time applicants, all ages and sexes); EU, EFTA and candidate reporting countries.",
       height=440)
def eu_asylum_first_time(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="year", columns="origin", values="applicants").fillna(0)
    order = p.loc[p.index.max()].sort_values(ascending=False).index.tolist()
    order = [o for o in order if o != "Other LAC countries"] + ["Other LAC countries"]
    fig = go.Figure()
    for i, origin in enumerate(order):
        color = t["other"] if origin == "Other LAC countries" else C[i]
        fig.add_trace(go.Scatter(x=p.index, y=p[origin], mode="lines+markers", name=origin,
                                 line=dict(color=color, width=2), marker=dict(size=6, color=color),
                                 hovertemplate="%{y:,.0f}<extra>" + origin + "</extra>"))
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=2),
                      yaxis=dict(**magnitude_axis(p.max().max() * 1.1), title_text="Applicants"))
    return fig


# ---- 03 Household surveys ---------------------------------------------------------------------

@chart("svy_availability",
       title="Household-survey rounds with harmonized microdata, by country and year",
       subtitle="IDB harmonized bank (26 countries), Spain's EPA extract and the US surveys used in this ecosystem",
       source="IDB SCL harmonized household surveys inventory (January 2025 snapshot); IPUMS USA/CPS; INE EPA via the HDMF project.",
       note="Each cell is a round with a harmonized file. Hover to see the survey. Later rounds (2023–2025) exist locally for several countries but are not in the inventory snapshot.",
       height=760, max_rows=0)
def svy_availability(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    fam_code = {"IDB harmonized household surveys": 1, "Spain EPA (HDMF)": 2, "US surveys (IPUMS)": 3}
    lac_rows = sorted({r for r, f in zip(df.row, df.family) if fam_code[f] == 1}, key=sort_key)
    rows = lac_rows + ["Spain: EPA", "United States: CPS ASEC", "United States: ACS"]
    years = list(range(1986, 2026))
    z = [[None] * len(years) for _ in rows]
    txt = [[""] * len(years) for _ in rows]
    for _, r in df.iterrows():
        if r.row in rows and r.year in years:
            i, j = rows.index(r.row), years.index(int(r.year))
            z[i][j] = fam_code[r.family]
            txt[i][j] = r.survey
    colorscale = [[0, C[0]], [0.5, C[0]], [0.5, C[1]], [0.75, C[1]], [0.75, C[2]], [1, C[2]]]
    fig = go.Figure(go.Heatmap(z=z, x=years, y=rows, zmin=0.5, zmax=3.5, colorscale=colorscale, showscale=False,
                               xgap=2, ygap=2, hoverongaps=False, customdata=txt,
                               hovertemplate="<b>%{y}</b> · %{x}<br>%{customdata}<extra></extra>"))
    for name, col in (("IDB harmonized LAC surveys", C[0]), ("Spain EPA (HDMF)", C[1]), ("US surveys (IPUMS)", C[2])):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=name,
                                 marker=dict(symbol="square", size=12, color=col, line=dict(width=0))))
    fig.update_layout(xaxis=dict(dtick=2, tickangle=-45, side="bottom", showgrid=False, tickfont=dict(size=11),
                                 range=[1985.5, 2025.5]),
                      yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=11)),
                      margin=dict(l=8, r=16, t=28, b=40))
    return fig


@chart("svy_employment_migrants_natives",
       title="Employment rate of foreign-born and native-born residents, ages 15–64",
       subtitle="Latest harmonized round per country; Spain's EPA 2024 and the US ACS 2024 use the same concept (born abroad)",
       source="IDB harmonized household surveys (migrante_ci, condocup_ci); INE EPA 2024 via HDMF; Census ACS 2024 PUMS (LAC-born, ages 16–64).",
       note="Employment follows each survey's national definition. The US row shows LAC-born residents only; natives are not in the extract.",
       height=460, max_rows=60)
def svy_employment_migrants_natives(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    p = df.pivot_table(index="country", columns="group", values="rate").reset_index()
    p = p.sort_values("Foreign-born", ascending=False)
    surveys = df.groupby("country").survey.agg(lambda s: " / ".join(dict.fromkeys(s)))
    p["survey"] = p.country.map(surveys)
    fig = dumbbell(p, "country", "Native-born", "Foreign-born", "Native-born", "Foreign-born", mode, t,
                   a_color=t["muted"], label_text=lambda v: f"{v:.0%}",
                   hover_a="<b>%{y}</b><br>Native-born: %{x:.1%}<extra></extra>",
                   hover_b="<b>%{y}</b><br>Foreign-born: %{x:.1%}<br>%{customdata}<extra></extra>")
    fig.data[-2].customdata = p.survey
    fig.update_xaxes(tickformat=".0%", range=[0.45, 0.9], title_text="Employed share of the population aged 15–64")
    fig.update_layout(margin=dict(r=56))
    return fig


# ---- 04 Global estimates ----------------------------------------------------------------------

@chart("gl_emigrants_destination",
       title="Where emigrants from Latin America and the Caribbean live, 1990–2024",
       subtitle="Stock of people born in a LAC country living abroad, by destination group (persons, 1 January)",
       source="FLown annual bilateral estimates (Azose and Raftery 2019, accessed via Gaskin and Abel 2025), summed over 48 LAC origins.",
       note="Modelled estimates: stocks are dated 1 January and carry uncertainty bands not shown here. UN DESA's mid-year figures differ slightly.",
       height=460)
def gl_emigrants_destination(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    order = ["United States", "Latin America and the Caribbean", "Spain", "Other countries"]
    p = df.pivot(index="year", columns="destination", values="emigrants").reindex(columns=order)
    shares = df.pivot(index="year", columns="destination", values="share_pct").reindex(columns=order)
    fig = go.Figure()
    for i, dest in enumerate(order):
        color = t["other"] if dest == "Other countries" else C[i]
        fig.add_trace(go.Scatter(x=p.index, y=p[dest], name=dest, mode="lines", stackgroup="one",
                                 line=dict(color=color, width=1.5), fillcolor=rgba(color, 0.62),
                                 customdata=shares[dest], hovertemplate="%{y:,.0f} (%{customdata:.1f}%)<extra>" + dest + "</extra>"))
    last = p.index.max()
    cum = p.loc[last].cumsum()
    for i, dest in enumerate(order):
        mid = cum[dest] - p.loc[last, dest] / 2
        fig.add_annotation(x=last, y=mid, text=f"{shares.loc[last, dest]:.0f}%", showarrow=False, xanchor="left",
                           xshift=6, font=dict(color=t["text2"], size=11))
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=5, range=[1990, 2024.3]),
                      yaxis=dict(**magnitude_axis(p.sum(axis=1).max() * 1.05), title_text="Persons"),
                      margin=dict(r=48))
    return fig


@chart("gl_immigrant_stock_lac",
       title="International migrants living in the 26 IDB borrowing countries, 1990 vs 2024",
       subtitle="Migrant stock by country of residence, all origins (mid-year estimates)",
       source="UN DESA, International Migrant Stock 2024.",
       height=760, max_rows=250)
def gl_immigrant_stock_lac(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    p = df.pivot(index="country", columns="year", values="immigrants")[[1990, 2024]]
    p = p.sort_values(2024, ascending=False).reset_index().rename(columns={1990: "y1990", 2024: "y2024"})
    p["change"] = p.y2024 / p.y1990 - 1
    fig = dumbbell(p, "country", "y1990", "y2024", "1990", "2024", mode, t,
                   hover_b="<b>%{y}</b><br>2024: %{x:,.0f}<br>change since 1990: %{customdata:+.0%}<extra></extra>")
    fig.data[-2].customdata = p.change
    fig.update_xaxes(**magnitude_axis(p[["y1990", "y2024"]].max().max() * 1.12), title_text="Persons")
    fig.update_layout(margin=dict(r=60))
    return fig


@chart("gl_displaced_lac_origin",
       title="Refugees and asylum-seekers from LAC countries, 1990–2024",
       subtitle="Persons under UNHCR's mandate by country of origin, wherever they are hosted",
       source="UNHCR Refugee Data Finder (population statistics), LAC countries as origin.",
       note="Excludes 'other people in need of international protection', the category UNHCR uses for most displaced Venezuelans (5.9 million in 2024); the table view includes it.",
       height=460)
def gl_displaced_lac_origin(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="year", columns="origin", values="refugees_asylum_seekers").fillna(0)
    order = p.loc[p.index.max()].sort_values(ascending=False).index.tolist()
    order = [o for o in order if o != "Other LAC countries"] + ["Other LAC countries"]
    fig = go.Figure()
    for i, origin in enumerate(order):
        color = t["other"] if origin == "Other LAC countries" else C[i]
        fig.add_trace(go.Scatter(x=p.index, y=p[origin], name=origin, mode="lines", stackgroup="one",
                                 line=dict(color=color, width=1.5), fillcolor=rgba(color, 0.62),
                                 hovertemplate="%{y:,.0f}<extra>" + origin + "</extra>"))
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=5, range=[1990, 2024.3]),
                      yaxis=dict(**magnitude_axis(p.sum(axis=1).max() * 1.05), title_text="Persons"))
    return fig


@chart("gl_remittances_gdp",
       title="Remittance inflows as a share of GDP, 2024",
       subtitle="Personal remittances received, LAC countries",
       source="KNOMAD / World Bank remittance inflows and WDI GDP, 2024 (World Bank estimates for the latest year).",
       height=720, max_rows=60)
def gl_remittances_gdp(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    d = df.sort_values("pct_gdp", ascending=False)
    fig = go.Figure(go.Bar(
        y=d.country, x=d.pct_gdp, orientation="h", marker=dict(color=C[0], cornerradius=4), width=0.62,
        text=[f"{v:.1f}%" for v in d.pct_gdp], textposition="outside", textfont=dict(color=t["text2"], size=11),
        cliponaxis=False, customdata=d.remittances_musd,
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of GDP · US$ %{customdata:,.0f} million<extra></extra>"))
    fig.update_layout(bargap=0.38, showlegend=False,
                      xaxis=dict(ticksuffix="%", showgrid=True, gridcolor=t["grid"], range=[0, d.pct_gdp.max() * 1.15],
                                 title_text="Share of GDP"),
                      yaxis=dict(autorange="reversed", showgrid=False), margin=dict(r=40))
    return fig


# ---- 05 Deportation data ----------------------------------------------------------------------

@chart("ddp_removals_fy",
       title="ICE removals by fiscal year and citizenship, FY2012–FY2026",
       subtitle="Removals executed by US Immigration and Customs Enforcement; FY2026 covers 1 October 2025 to 11 March 2026",
       source="ICE removal records released under FOIA, compiled by the Deportation Data Project (FY2023 deduplicated across the two releases).",
       note="FY2020–FY2022 are depressed by the pandemic and Title 42 expulsions, which are not removals. DDP flagged reliability concerns about the March 2026 release.",
       height=460)
def ddp_removals_fy(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    order = ["Mexico", "Guatemala", "Honduras", "El Salvador", "Other LAC countries", "Non-LAC citizens"]
    p = df.pivot(index="fiscal_year", columns="group", values="removals").reindex(columns=order)
    partial = df.groupby("fiscal_year").partial.first()
    fig = go.Figure()
    for i, grp in enumerate(order):
        color = t["other"] if grp == "Non-LAC citizens" else C[i]
        # the partial fiscal year wears a 45-degree hatch (semantic texture: provisional), full color otherwise
        fig.add_trace(go.Bar(x=[f"FY{y}" for y in p.index], y=p[grp], name=grp,
                             marker=dict(color=color, line=dict(color=t["surface"], width=1.5), cornerradius=3,
                                         pattern=dict(shape=["/" if partial[y] else "" for y in p.index],
                                                      fgcolor=color, bgcolor=t["surface"], solidity=0.45, size=7)),
                             hovertemplate="%{y:,.0f}<extra>" + grp + "</extra>"))
    totals = p.sum(axis=1)
    for y in (2012, 2016, 2019, 2021, 2024, 2025):
        fig.add_annotation(x=f"FY{y}", y=totals[y], text=fmt_num(totals[y]), showarrow=False, yshift=10,
                           font=dict(color=t["text2"], size=11))
    fig.add_annotation(x="FY2026", y=totals[2026], text="partial", showarrow=False, yshift=10,
                       font=dict(color=t["muted"], size=10))
    fig.update_layout(barmode="stack", bargap=0.3, hovermode="x unified",
                      xaxis=dict(tickfont=dict(size=11)),
                      yaxis=dict(**magnitude_axis(totals.max() * 1.1), title_text="Removals"))
    return fig


@chart("ddp_tps_backlog",
       title="Temporary Protected Status applications: monthly flows and pending stock, 2015–2026",
       subtitle="Applications received, applications decided, and the stock pending at month end",
       source="USCIS TPS application records (form I-821) released in Mukherjee v. USCIS, compiled by the Deportation Data Project; February 2026 is partial (to 11 February).",
       note="An application is not a person: renewals repeat. Received and decided follow different clocks (filing date vs decision date), so the stock is the only column that nets them.",
       height=560, max_rows=0)
def ddp_tps_backlog(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    d = df.copy()
    d["date"] = pd.to_datetime(d.month + "-01")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                        subplot_titles=("Applications per month", "Applications pending at month end"))
    fig.add_trace(go.Scatter(x=d.date, y=d.received, name="Received", mode="lines", line=dict(color=C[0], width=2),
                             hovertemplate="%{y:,.0f}<extra>Received</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.date, y=d.decided, name="Decided", mode="lines", line=dict(color=C[1], width=2),
                             hovertemplate="%{y:,.0f}<extra>Decided</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.date, y=d.pending_stock, name="Pending stock", mode="lines",
                             line=dict(color=C[0], width=2), fill="tozeroy", fillcolor=rgba(C[0], 0.14),
                             hovertemplate="%{y:,.0f}<extra>Pending</extra>"), row=2, col=1)
    for ann in fig.layout.annotations:
        ann.update(font=dict(size=12, color=t["text2"]), x=0, xanchor="left")
    fig.update_layout(hovermode="x unified", legend=dict(y=1.08))
    fig.update_yaxes(**magnitude_axis(d[["received", "decided"]].max().max() * 1.1), row=1, col=1)
    fig.update_yaxes(**magnitude_axis(d.pending_stock.max() * 1.1), row=2, col=1)
    fig.update_xaxes(showgrid=False, dtick="M12", tickformat="%Y", row=2, col=1)
    return fig


@chart("ddp_third_country",
       title="Removals to a country other than the person's own, FY2012–FY2026",
       subtitle="Departure country different from citizenship country; all citizenships and LAC citizens",
       source="ICE removal records released under FOIA, compiled by the Deportation Data Project; FY2026 partial (to 11 March 2026).",
       height=400)
def ddp_third_country(df: pd.DataFrame, mode: str, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="fiscal_year", columns="group", values="removals")
    fig = go.Figure()
    for i, grp in enumerate(["All citizenships", "LAC citizens"]):
        fig.add_trace(go.Scatter(x=[f"FY{y}" for y in p.index], y=p[grp], name=grp, mode="lines+markers",
                                 line=dict(color=C[i], width=2), marker=dict(size=7, color=C[i]),
                                 hovertemplate="%{y:,.0f}<extra>" + grp + "</extra>"))
        # label the peak (the last complete fiscal year), not the partial stub at the end
        peak = p[grp].idxmax()
        fig.add_annotation(x=f"FY{peak}", y=p.loc[peak, grp], text=f"{p.loc[peak, grp]:,.0f}", showarrow=False,
                           yshift=14 if i == 0 else -16, font=dict(color=t["text2"], size=11))
    fig.update_layout(hovermode="x unified", xaxis=dict(tickfont=dict(size=11)),
                      yaxis=dict(**magnitude_axis(p.max().max() * 1.1), title_text="Removals"), margin=dict(r=56))
    return fig


# ---- rendering --------------------------------------------------------------------------------

def _table_html(df: pd.DataFrame, max_rows: int) -> str:
    if max_rows == 0:
        return "<p class=\"chart__tablenote\">The full table is available as CSV (link above).</p>"
    d = df.copy()
    truncated = len(d) > max_rows
    d = d.head(max_rows)
    cols = list(d.columns)
    rows = []
    for _, r in d.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                if pd.isna(v):
                    s = ""
                elif abs(v) < 2 and c not in ("year",):
                    s = f"{v:.3f}"
                else:
                    s = f"{v:,.1f}" if v != int(v) else f"{int(v):,}"
            elif isinstance(v, (int,)) or (hasattr(v, "dtype") and "int" in str(getattr(v, "dtype", ""))):
                s = f"{int(v)}" if c in ("year", "fiscal_year", "start", "end") else f"{int(v):,}"
            else:
                s = html.escape(str(v))
            cells.append(f"<td>{s}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    note = f"<p class=\"chart__tablenote\">First {max_rows} of {len(df)} rows; the CSV has all of them.</p>" if truncated else ""
    return f"<div class=\"tablewrap\"><table class=\"data-table\"><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>{note}"


def build_figure(cid: str, df: pd.DataFrame, mode: str, web: bool) -> go.Figure:
    meta = CHARTS[cid]
    t = THEME[mode]
    fig = meta["build"](df, mode, t)
    fig.update_layout(template=f"eco_{mode}{'_web' if web else ''}", height=meta["height"])
    return fig


def write_fragment(cid: str, df: pd.DataFrame) -> str:
    meta = CHARTS[cid]
    fig = build_figure(cid, df, "dark", web=True)
    div = fig.to_html(full_html=False, include_plotlyjs=False, include_mathjax=False, div_id=f"plot-{cid}",
                      config=PLOTLY_CONFIG, default_width="100%", default_height=f"{meta['height']}px")
    note = f"<p class=\"chart__note\">{html.escape(meta['note'])}</p>" if meta.get("note") else ""
    frag = f"""<figure class="chart" id="fig-{cid}">
  <figcaption class="chart__head">
    <h3 class="chart__title">{html.escape(meta['title'])}</h3>
    <p class="chart__sub">{html.escape(meta['subtitle'])}</p>
  </figcaption>
  <div class="chart__plot">{div}</div>
  <div class="chart__foot">
    <p class="chart__source">Source: {html.escape(meta['source'])}</p>
    {note}
    <p class="chart__links"><a href="figures/light/{cid}.png" download>PNG, light</a> · <a href="figures/dark/{cid}.png" download>PNG, dark</a> · <a href="data/{cid}.csv">CSV</a></p>
  </div>
  <details class="chart__table"><summary>Table view</summary>{_table_html(df, meta['max_rows'])}</details>
</figure>"""
    (CHARTS_OUT / f"{cid}.html").write_text(frag, encoding="utf-8")
    return frag


def write_png(cid: str, df: pd.DataFrame) -> None:
    meta = CHARTS[cid]
    for mode in ("dark", "light"):
        t = THEME[mode]
        fig = build_figure(cid, df, mode, web=False)
        h = max(560, meta["height"] + 140)
        fig.update_layout(
            width=1400, height=h,
            title=dict(text=f"<b>{meta['title']}</b><br><span style='font-size:14px;color:{t['text2']}'>{meta['subtitle']}</span>",
                       x=0.03, xanchor="left", y=0.96, yanchor="top", font=dict(size=21, color=t["text"])),
            margin=dict(t=135, b=96, l=70, r=70), legend=dict(y=1.0, yanchor="bottom"))
        fig.add_annotation(text=f"Source: {meta['source']}", xref="paper", yref="paper", x=0, y=-0.09 * 460 / meta["height"] - 0.04,
                           showarrow=False, xanchor="left", yanchor="top", align="left",
                           font=dict(size=11, color=t["muted"]))
        fig.write_image(str(FIG_OUT / mode / f"{cid}.png"), width=1400, height=h, scale=2)


def build_all(png: bool = True, only: list[str] | None = None) -> dict[str, str]:
    fragments = {}
    for cid in CHARTS:
        if only and cid not in only:
            continue
        df = pd.read_csv(DATA_OUT / f"{cid}.csv")
        fragments[cid] = write_fragment(cid, df)
        if png:
            write_png(cid, df)
        print(f"  [charts] {cid}: fragment{' + png' if png else ''}")
    return fragments


if __name__ == "__main__":
    build_all()
