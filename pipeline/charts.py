"""Chart builders: data/<id>.csv -> Plotly figure -> HTML fragment (site), PNG (slides), public CSV.

Projection first. Light theme, large type, no subtitles: what a reader must know to
read the chart lives in the footnote ("Note: ... Source: ..."). On the site each chart
sizes itself to the screen, so title, plot and footnote fit without scrolling.

Every chart follows the dataviz method: the form is chosen by the data's job,
categorical hues are assigned in fixed slot order (never cycled), marks are thin,
grids are hairlines, a legend is present for two or more series, text uses text
tokens, and every chart ships a table view plus its CSV.
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

MODE = "light"
PLOTLY_CONFIG = dict(responsive=True, displaylogo=False, displayModeBar=False)
AGE_LABELS = [f"{a}-{a + 4}" for a in range(0, 80, 5)] + ["80+"]
PNG_W, PNG_H = 1600, 900

CHARTS: dict[str, dict] = {}


def chart(cid: str, *, title: str, source: str, note: str | None = None,
          public: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
          table: Callable[[pd.DataFrame], pd.DataFrame] | None = None):
    """Register a chart. `public` turns the internal table into the published CSV
    (readable headers, no technical columns); `table` builds the on-page table view
    (defaults to the public CSV)."""
    def deco(fn: Callable[[pd.DataFrame, dict], go.Figure]):
        CHARTS[cid] = dict(id=cid, title=title, source=source, note=note, build=fn,
                           public=public or (lambda d: d), table=table)
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
    for step in (1e4, 2.5e4, 5e4, 1e5, 2.5e5, 5e5, 1e6, 2e6, 2.5e6, 5e6, 1e7):
        if vmax / step <= 6:
            break
    ticks = [i * step for i in range(int(vmax // step) + 2)]
    return dict(tickvals=ticks, ticktext=[fmt_num(x) if x else "0" for x in ticks], range=[0, vmax])


def top_n_with_other(s: pd.Series, n: int, other_label: str) -> pd.Series:
    """Keep the n largest values and fold the rest into one labelled 'Other' row."""
    s = s.sort_values(ascending=False)
    if len(s) <= n + 1:
        return s
    out = s.iloc[:n].copy()
    out[other_label.format(k=len(s) - n)] = s.iloc[n:].sum()
    return out


def dumbbell(df: pd.DataFrame, cat: str, a: str, b: str, a_label: str, b_label: str, t: dict,
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
                                     line=dict(color=t["baseline"], width=3), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=df[a], y=cats, mode="markers", name=a_label,
        marker=dict(color=a_color, size=12, line=dict(width=2, color=t["surface"])),
        hovertemplate=hover_a or f"<b>%{{y}}</b><br>{a_label}: %{{x:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=df[b], y=cats, mode="markers", name=b_label,
        marker=dict(color=C[0], size=13, line=dict(width=2, color=t["surface"])),
        hovertemplate=hover_b or f"<b>%{{y}}</b><br>{b_label}: %{{x:,.0f}}<extra></extra>"))
    # the value label sits next to its own (later) dot, on the side away from the earlier dot, so it
    # never covers a mark and never reads as the earlier value; an invisible marker keeps the text offset
    labels = [label_text(v) if label_text else fmt(v) for v in df[b]]
    side = ["middle left" if (pd.notna(va) and pd.notna(vb) and vb < va) else "middle right"
            for va, vb in zip(df[a], df[b])]
    fig.add_trace(go.Scatter(x=df[b], y=cats, mode="markers+text", text=labels, textposition=side,
                             textfont=dict(color=t["text2"], size=14), cliponaxis=False,
                             marker=dict(size=15, color="rgba(0,0,0,0)", line=dict(width=0)),
                             showlegend=False, hoverinfo="skip"))
    fig.update_yaxes(categoryorder="array", categoryarray=cats, autorange="reversed", showgrid=True,
                     gridcolor=t["grid"], tickfont=dict(color=t["text"]))
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"])
    return fig


def end_labels(fig: go.Figure, x_last: float, ys: dict, t: dict, y_top: float, x_text: float,
               min_gap: float = 0.08) -> None:
    """Direct labels at the right end of each line. When two ends are close, the labels
    are spread apart (data units, so it holds at any screen size) and tied to their line
    end with a thin leader line, instead of stacking on top of each other."""
    items = sorted(ys.items(), key=lambda kv: kv[1])
    gap = y_top * min_gap
    pos: list[float] = []
    for _, v in items:
        pos.append(v if not pos else max(v, pos[-1] + gap))
    overflow = pos[-1] - y_top * 0.97 if pos else 0
    if overflow > 0:
        pos = [p - overflow for p in pos]
    for (name, v), y in zip(items, pos):
        fig.add_annotation(x=x_last, y=v, ax=x_text, ay=y, axref="x", ayref="y", text=name,
                           showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=t["baseline"],
                           xanchor="left", font=dict(color=t["text"], size=14))


# ---- 00 overview ------------------------------------------------------------------------------

@chart("ov_coverage_timeline",
       title="Years covered by each source",
       source="producers' documentation of each source.",
       note="Each bar spans the years available. Hover a bar to see how often the data come out.",
       public=lambda d: d.rename(columns={"family": "Section", "product": "Source", "start": "First year",
                                          "end": "Last year", "periodicity": "How often", "unit": "Unit"}))
def ov_coverage_timeline(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    fams = list(dict.fromkeys(df.family))
    products = list(dict.fromkeys(df["product"]))
    fig = go.Figure()
    for i, fam in enumerate(fams):
        d = df[df.family == fam]
        fig.add_trace(go.Bar(
            y=d["product"], x=d.end - d.start + 1, base=d.start, orientation="h", name=fam,
            marker=dict(color=C[i], cornerradius=4), width=0.6,
            customdata=d[["start", "end", "periodicity", "unit"]].values,
            hovertemplate="<b>%{y}</b><br>%{customdata[0]}–%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<extra></extra>"))
    fig.update_layout(barmode="overlay",
                      xaxis=dict(range=[1979, 2027.5], tickvals=[1980, 1990, 2000, 2010, 2020, 2026],
                                 showgrid=True, gridcolor=t["grid"]),
                      yaxis=dict(categoryorder="array", categoryarray=products, autorange="reversed",
                                 showgrid=False, tickfont=dict(size=14, color=t["text"])))
    return fig


# ---- 01 United States -------------------------------------------------------------------------

def _us_stock_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot(index="country", columns="year", values="population").round(0)
    p = p.sort_values(p.columns.max(), ascending=False)
    p.columns = [str(c) for c in p.columns]
    return p.reset_index().rename(columns={"country": "Country of birth"})


@chart("us_stock_by_country",
       title="People born in LAC living in the US, 2014 and 2024",
       source="US Census Bureau, American Community Survey 2014 and 2024 (public-use microdata).",
       note="Foreign-born residents: naturalized citizens and non-citizens. The 15 largest groups; the rest are combined.",
       public=_us_stock_public)
def us_stock_by_country(df: pd.DataFrame, t: dict) -> go.Figure:
    p = df.pivot(index="country", columns="year", values="population")
    s24 = top_n_with_other(p[2024], 15, "Other LAC countries ({k})")
    s14 = p[2014].reindex(s24.index)
    if s24.index[-1].startswith("Other"):
        s14.iloc[-1] = p[2014].drop(s24.index[:-1]).sum()
    d = pd.DataFrame({"country": s24.index, "y2014": s14.values, "y2024": s24.values})
    d["change"] = d.y2024 / d.y2014 - 1
    fig = dumbbell(d, "country", "y2014", "y2024", "2014", "2024", t,
                   hover_b="<b>%{y}</b><br>2024: %{x:,.0f}<br>change since 2014: %{customdata:+.0%}<extra></extra>")
    fig.data[-2].customdata = d.change
    fig.update_xaxes(**magnitude_axis(d[["y2014", "y2024"]].max().max() * 1.1), title_text="People")
    fig.update_layout(margin=dict(r=70))
    return fig


def _pyramid_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot_table(index="age_group", columns=["sex", "year"], values="share_pct").reindex(AGE_LABELS)
    p.columns = [f"{s} {y} (%)" for s, y in p.columns]
    return p.round(2).reset_index().rename(columns={"age_group": "Age group"})


@chart("us_age_pyramid",
       title="Age of LAC-born residents in the US, 2014 and 2024",
       source="US Census Bureau, American Community Survey 2014 and 2024 (public-use microdata).",
       note="Share of all LAC-born residents by age and sex. The outline shows 2014.",
       public=_pyramid_public)
def us_age_pyramid(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    fig = go.Figure()
    for year, outline in ((2024, False), (2014, True)):
        for sex, sign, col in (("Men", -1, C[0]), ("Women", 1, C[1])):
            d = df[(df.year == year) & (df.sex == sex)].set_index("age_group").reindex(AGE_LABELS)
            kwargs = dict(x=sign * d.share_pct, y=AGE_LABELS, orientation="h", customdata=d.share_pct,
                          hovertemplate=f"{sex}, {year}, %{{y}}: %{{customdata:.1f}}%<extra></extra>")
            if outline:
                fig.add_trace(go.Bar(name="2014 (outline)", legendgroup="2014", showlegend=(sex == "Men"),
                                     marker=dict(color="rgba(0,0,0,0)", line=dict(color=t["text"], width=1.5)),
                                     **kwargs))
            else:
                fig.add_trace(go.Bar(name=f"{sex}, 2024", marker=dict(color=col, cornerradius=3), **kwargs))
    m = df.share_pct.max() * 1.15
    ticks = [v for v in (-8, -6, -4, -2, 0, 2, 4, 6, 8) if abs(v) <= m]
    fig.update_layout(barmode="overlay", bargap=0.15,
                      xaxis=dict(tickvals=ticks, ticktext=[f"{abs(v)}%" for v in ticks], range=[-m, m],
                                 showgrid=True, gridcolor=t["grid"], title_text="Share of LAC-born residents"),
                      yaxis=dict(categoryorder="array", categoryarray=AGE_LABELS, showgrid=False, title_text="Age",
                                 tickfont=dict(color=t["text"])))
    fig.add_annotation(x=-m * 0.95, y=16, text="<b>Men</b>", showarrow=False, xanchor="left",
                       font=dict(color=t["text"], size=15))
    fig.add_annotation(x=m * 0.95, y=16, text="<b>Women</b>", showarrow=False, xanchor="right",
                       font=dict(color=t["text"], size=15))
    return fig


# ---- 02 Europe --------------------------------------------------------------------------------

def _eu_born_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot_table(index="country", columns="host_name", values="population", aggfunc="sum").fillna(0)
    order = d.groupby("host_name").population.sum().sort_values(ascending=False).index.tolist()
    order = [h for h in order if h != "Other reporting countries"] + ["Other reporting countries"]
    p = p[[h for h in order if h in p.columns]]
    p["Total"] = p.sum(axis=1)
    p = p.sort_values("Total", ascending=False).round(0)
    return p.reset_index().rename(columns={"country": "Country of birth"})


@chart("eu_lac_born_2024",
       title="People born in LAC living in Europe, 2024",
       source="Eurostat, population on 1 January by country of birth.",
       note="The 12 largest groups, split by country of residence. France and Germany do not report this figure.",
       public=_eu_born_public)
def eu_lac_born_2024(df: pd.DataFrame, t: dict) -> go.Figure:
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
                             marker=dict(color=color, line=dict(color=t["surface"], width=2)),
                             hovertemplate=f"Born in %{{y}}, living in {h.host_name}: %{{x:,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(x=totals[keep].values, y=keep, mode="text", text=[fmt_num(v) for v in totals[keep]],
                             textposition="middle right", textfont=dict(color=t["text2"], size=14),
                             showlegend=False, hoverinfo="skip", cliponaxis=False))
    fig.update_layout(barmode="stack", bargap=0.3,
                      xaxis=dict(**magnitude_axis(totals[keep].max() * 1.12), showgrid=True, gridcolor=t["grid"],
                                 title_text="People"),
                      yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(color=t["text"])),
                      margin=dict(r=70))
    return fig


def _permits_public(d: pd.DataFrame) -> pd.DataFrame:
    order = ["Employment", "Family", "Education", "Other reasons"]
    p = d.pivot(index="year", columns="reason", values="permits").reindex(columns=order).fillna(0)
    p["Total"] = p.sum(axis=1)
    p["Reporting countries"] = d.groupby("year").n_reporting.max()
    return p.round(0).reset_index().rename(columns={"year": "Year"})


@chart("eu_first_permits_reason",
       title="First residence permits for LAC citizens in Europe, 2010–2025",
       source="Eurostat, first residence permits by reason and citizenship.",
       note="A permit is not a person. More countries report over time: Germany starts in 2019.",
       public=_permits_public)
def eu_first_permits_reason(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    order = ["Employment", "Family", "Education", "Other reasons"]
    p = df.pivot(index="year", columns="reason", values="permits").reindex(columns=order).fillna(0)
    fig = go.Figure()
    for i, reason in enumerate(order):
        fig.add_trace(go.Bar(x=p.index, y=p[reason], name=reason,
                             marker=dict(color=C[i], line=dict(color=t["surface"], width=2), cornerradius=3),
                             hovertemplate="%{y:,.0f}<extra>" + reason + "</extra>"))
    totals = p.sum(axis=1)
    for y in (2010, 2015, 2019, 2022, 2025):
        if y in totals.index:
            fig.add_annotation(x=y, y=totals[y], text=fmt_num(totals[y]), showarrow=False, yshift=12,
                               font=dict(color=t["text"], size=14))
    fig.update_layout(barmode="stack", bargap=0.3, hovermode="x unified",
                      xaxis=dict(dtick=1, tickangle=0, tickfont=dict(size=13)),
                      yaxis=dict(**magnitude_axis(totals.max() * 1.12), title_text="Permits"))
    return fig


def _asylum_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot(index="year", columns="origin", values="applicants").fillna(0)
    order = p.loc[p.index.max()].sort_values(ascending=False).index.tolist()
    order = [o for o in order if o != "Other LAC countries"] + ["Other LAC countries"]
    return p[order].round(0).reset_index().rename(columns={"year": "Year"})


@chart("eu_asylum_first_time",
       title="First-time asylum applicants from LAC in Europe, 2008–2025",
       source="Eurostat, asylum applicants by citizenship.",
       note="The three largest groups in 2025. The table lists five.",
       public=_asylum_public)
def eu_asylum_first_time(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="year", columns="origin", values="applicants").fillna(0)
    last = p.index.max()
    named = [o for o in p.loc[last].sort_values(ascending=False).index if o != "Other LAC countries"][:3]
    series = {o: p[o] for o in named}
    series["Other LAC countries"] = p.sum(axis=1) - sum(series.values())
    fig = go.Figure()
    for i, (origin, s) in enumerate(series.items()):
        color = t["other"] if origin.startswith("Other") else C[i]
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=origin,
                                 line=dict(color=color, width=3.5),
                                 hovertemplate="%{y:,.0f}<extra>" + origin + "</extra>"))
    vmax = max(s.max() for s in series.values()) * 1.1
    end_labels(fig, last, {o: s.loc[last] for o, s in series.items()}, t, y_top=vmax, x_text=last + 0.9)
    fig.update_layout(hovermode="x unified", margin=dict(r=200),
                      xaxis=dict(dtick=2, range=[2008, last + 0.2]),
                      yaxis=dict(**magnitude_axis(vmax), title_text="Applicants"))
    return fig


# ---- 03 Household surveys ---------------------------------------------------------------------

FAM_LABEL = {"IDB harmonized household surveys": "Harmonized LAC household surveys",
             "Spain EPA (HDMF)": "Spain: Labour Force Survey",
             "US surveys (IPUMS)": "US surveys"}
ROW_LABEL = {"Spain: EPA": "Spain", "United States: CPS ASEC": "US: Current Population Survey",
             "United States: ACS": "US: American Community Survey"}


def _avail_public(d: pd.DataFrame) -> pd.DataFrame:
    out = d.assign(row=d.row.replace(ROW_LABEL), family=d.family.map(FAM_LABEL))
    out = out[["row", "family", "year", "survey"]]
    out["survey"] = out.survey.str.replace(r"\s*\(.*\)", "", regex=True).str.replace(", HDMF harmonization", "")
    return out.rename(columns={"row": "Country", "family": "Source", "year": "Year", "survey": "Survey"})


def _avail_table(d: pd.DataFrame) -> pd.DataFrame:
    pub = _avail_public(d)
    g = pub.groupby(["Country", "Source"], sort=False)
    out = g.agg(**{"Years with data": ("Year", "nunique"), "First year": ("Year", "min"), "Last year": ("Year", "max"),
                   "Surveys": ("Survey", lambda s: " / ".join(dict.fromkeys(" / ".join(s).split(" / "))))})
    return out.reset_index()


@chart("svy_availability",
       title="Household surveys with harmonized data, by country and year",
       source="IDB Harmonized Household Surveys; IPUMS; INE (Spain).",
       note="One cell is one year with a harmonized survey. LAC rounds as listed in January 2025; newer rounds exist for several countries.",
       public=_avail_public, table=_avail_table)
def svy_availability(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    fam_code = {"IDB harmonized household surveys": 1, "Spain EPA (HDMF)": 2, "US surveys (IPUMS)": 3}
    lac_rows = sorted({r for r, f in zip(df.row, df.family) if fam_code[f] == 1}, key=sort_key)
    rows_raw = lac_rows + ["Spain: EPA", "United States: CPS ASEC", "United States: ACS"]
    rows = [ROW_LABEL.get(r, r) for r in rows_raw]
    years = list(range(1986, 2026))
    z = [[None] * len(years) for _ in rows]
    txt = [[""] * len(years) for _ in rows]
    clean = _avail_public(df)
    for (_, r), survey in zip(df.iterrows(), clean.Survey):
        if r.row in rows_raw and r.year in years:
            i, j = rows_raw.index(r.row), years.index(int(r.year))
            z[i][j] = fam_code[r.family]
            txt[i][j] = survey
    colorscale = [[0, C[0]], [0.5, C[0]], [0.5, C[1]], [0.75, C[1]], [0.75, C[2]], [1, C[2]]]
    fig = go.Figure(go.Heatmap(z=z, x=years, y=rows, zmin=0.5, zmax=3.5, colorscale=colorscale, showscale=False,
                               xgap=2, ygap=2, hoverongaps=False, customdata=txt,
                               hovertemplate="<b>%{y}</b> · %{x}<br>%{customdata}<extra></extra>"))
    for name, col in (("Harmonized LAC household surveys", C[0]), ("Spain: Labour Force Survey", C[1]),
                      ("US surveys", C[2])):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=name,
                                 marker=dict(symbol="square", size=14, color=col, line=dict(width=0))))
    fig.update_layout(xaxis=dict(tickvals=list(range(1986, 2026, 4)), showgrid=False, range=[1985.5, 2025.5],
                                 tickfont=dict(size=14)),
                      yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=13, color=t["text"])),
                      margin=dict(l=8, r=16, t=48, b=40))
    return fig


ROWNAME = {"United States (LAC-born only)": "United States"}


def _emp_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.assign(country=d.country.replace(ROWNAME)).pivot_table(index="country", columns="group", values="rate")
    p = (p * 100).round(1).reindex(columns=["Native-born", "Foreign-born"])
    surveys = d.assign(country=d.country.replace(ROWNAME)).groupby("country").survey.agg(
        lambda s: " / ".join(dict.fromkeys(s.str.replace(r"\s*\(.*\)", "", regex=True).str.replace(" PUMS", ""))))
    p.insert(0, "Survey", surveys)
    p = p.sort_values("Foreign-born", ascending=False)
    return p.reset_index().rename(columns={"country": "Country", "Native-born": "Born in the country (%)",
                                           "Foreign-born": "Born abroad (%)"})


@chart("svy_employment_migrants_natives",
       title="Employment rate: born abroad vs born in the country, ages 15–64",
       source="IDB Harmonized Household Surveys; INE (Spain); US Census Bureau.",
       note="Latest year per country, 2022–2024. National definitions of employment. Spain and the US: people born in LAC, ages 16–64; no US rate for people born in the country.",
       public=_emp_public)
def svy_employment_migrants_natives(df: pd.DataFrame, t: dict) -> go.Figure:
    d = df.assign(country=df.country.replace(ROWNAME))
    p = d.pivot_table(index="country", columns="group", values="rate").reset_index()
    # countries with both rates first, by the migrant rate; the US (migrants only) last, on purpose
    p = p.assign(_one=p["Native-born"].isna()).sort_values(["_one", "Foreign-born"], ascending=[True, False])
    fig = dumbbell(p, "country", "Native-born", "Foreign-born", "Born in the country", "Born abroad", t,
                   a_color=t["muted"], label_text=lambda v: f"{v:.0%}",
                   hover_a="<b>%{y}</b><br>Born in the country: %{x:.1%}<extra></extra>",
                   hover_b="<b>%{y}</b><br>Born abroad: %{x:.1%}<extra></extra>")
    fig.update_xaxes(tickformat=".0%", range=[0.5, 0.85], dtick=0.05,
                     title_text="Employed share of the population aged 15–64")
    fig.update_layout(margin=dict(r=60))
    return fig


# ---- 04 Global estimates ----------------------------------------------------------------------

DEST_ORDER = ["United States", "Latin America and the Caribbean", "Spain", "Other countries"]


def _emig_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot(index="year", columns="destination", values="emigrants").reindex(columns=DEST_ORDER)
    p["Total"] = p.sum(axis=1)
    return p.round(0).reset_index().rename(columns={"year": "Year"})


@chart("gl_emigrants_destination",
       title="Where LAC emigrants live, 1990–2024",
       source="Azose and Raftery (2019) estimates, via Gaskin and Abel (2025).",
       note="Modelled estimates of people born in a LAC country, on 1 January. Labels show the 2024 shares.",
       public=_emig_public)
def gl_emigrants_destination(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="year", columns="destination", values="emigrants").reindex(columns=DEST_ORDER)
    shares = df.pivot(index="year", columns="destination", values="share_pct").reindex(columns=DEST_ORDER)
    fig = go.Figure()
    for i, dest in enumerate(DEST_ORDER):
        color = t["other"] if dest == "Other countries" else C[i]
        fig.add_trace(go.Scatter(x=p.index, y=p[dest], name=dest, mode="lines", stackgroup="one",
                                 line=dict(color=color, width=1.5), fillcolor=rgba(color, 0.7),
                                 customdata=shares[dest],
                                 hovertemplate="%{y:,.0f} (%{customdata:.1f}%)<extra>" + dest + "</extra>"))
    last = p.index.max()
    cum = p.loc[last].cumsum()
    for dest in DEST_ORDER:
        mid = cum[dest] - p.loc[last, dest] / 2
        fig.add_annotation(x=last, y=mid, text=f"<b>{shares.loc[last, dest]:.0f}%</b>", showarrow=False,
                           xanchor="left", xshift=8, font=dict(color=t["text"], size=15))
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=5, range=[1990, last + 0.3]),
                      yaxis=dict(**magnitude_axis(p.sum(axis=1).max() * 1.05), title_text="People"),
                      margin=dict(r=64))
    return fig


def _stock_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot(index="country", columns="year", values="immigrants")
    p = p.sort_values(p.columns.max(), ascending=False)
    p.columns = [str(c) for c in p.columns]
    return p.round(0).reset_index().rename(columns={"country": "Country of residence"})


@chart("gl_immigrant_stock_lac",
       title="Migrants living in IDB borrowing countries, 1990 and 2024",
       source="UN DESA, International Migrant Stock 2024.",
       note="International migrants of all origins, at mid-year. The 15 largest; the rest are combined.",
       public=_stock_public)
def gl_immigrant_stock_lac(df: pd.DataFrame, t: dict) -> go.Figure:
    p = df.pivot(index="country", columns="year", values="immigrants")
    s24 = top_n_with_other(p[2024], 15, "Other {k} countries")
    s90 = p[1990].reindex(s24.index)
    if s24.index[-1].startswith("Other"):
        s90.iloc[-1] = p[1990].drop(s24.index[:-1]).sum()
    d = pd.DataFrame({"country": s24.index, "y1990": s90.values, "y2024": s24.values})
    d["change"] = d.y2024 / d.y1990 - 1
    fig = dumbbell(d, "country", "y1990", "y2024", "1990", "2024", t,
                   hover_b="<b>%{y}</b><br>2024: %{x:,.0f}<br>change since 1990: %{customdata:+.0%}<extra></extra>")
    fig.data[-2].customdata = d.change
    fig.update_xaxes(**magnitude_axis(d[["y1990", "y2024"]].max().max() * 1.1), title_text="People")
    fig.update_layout(margin=dict(r=70))
    return fig


def _displaced_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot(index="year", columns="origin", values="refugees_asylum_seekers").fillna(0)
    order = p.loc[p.index.max()].sort_values(ascending=False).index.tolist()
    order = [o for o in order if o != "Other LAC countries"] + ["Other LAC countries"]
    p = p[order]
    p["Total"] = p.sum(axis=1)
    p["Other people in need of international protection"] = d.groupby("year").oip.sum()
    return p.round(0).reset_index().rename(columns={"year": "Year"})


@chart("gl_displaced_lac_origin",
       title="Refugees and asylum-seekers from LAC, 1990–2024",
       source="UNHCR Refugee Data Finder.",
       note="By country of origin, wherever they live. Excludes 5.9 million displaced Venezuelans that UNHCR counts in another category (2024).",
       public=_displaced_public)
def gl_displaced_lac_origin(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="year", columns="origin", values="refugees_asylum_seekers").fillna(0)
    order = p.loc[p.index.max()].sort_values(ascending=False).index.tolist()
    order = [o for o in order if o != "Other LAC countries"] + ["Other LAC countries"]
    fig = go.Figure()
    for i, origin in enumerate(order):
        color = t["other"] if origin == "Other LAC countries" else C[i]
        fig.add_trace(go.Scatter(x=p.index, y=p[origin], name=origin, mode="lines", stackgroup="one",
                                 line=dict(color=color, width=1.5), fillcolor=rgba(color, 0.7),
                                 hovertemplate="%{y:,.0f}<extra>" + origin + "</extra>"))
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=5, range=[1990, 2024.3]),
                      yaxis=dict(**magnitude_axis(p.sum(axis=1).max() * 1.05), title_text="People"))
    return fig


@chart("gl_remittances_gdp",
       title="Remittances received as a share of GDP, 2024",
       source="World Bank and KNOMAD.",
       note="The 15 countries with the highest share. The table lists all countries.",
       public=lambda d: d[["country", "remittances_musd", "pct_gdp"]].sort_values("pct_gdp", ascending=False).rename(
           columns={"country": "Country", "remittances_musd": "Remittances (US$ million)", "pct_gdp": "Share of GDP (%)"}))
def gl_remittances_gdp(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    d = df.sort_values("pct_gdp", ascending=False).head(15)
    fig = go.Figure(go.Bar(
        y=d.country, x=d.pct_gdp, orientation="h", marker=dict(color=C[0], cornerradius=4), width=0.62,
        text=[f"{v:.1f}%" for v in d.pct_gdp], textposition="outside", textfont=dict(color=t["text"], size=14),
        cliponaxis=False, customdata=d.remittances_musd,
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of GDP · US$ %{customdata:,.0f} million<extra></extra>"))
    fig.update_layout(showlegend=False, margin=dict(t=20, r=60),
                      xaxis=dict(ticksuffix="%", showgrid=True, gridcolor=t["grid"], range=[0, d.pct_gdp.max() * 1.15],
                                 title_text="Share of GDP"),
                      yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(color=t["text"])))
    return fig


# ---- 05 Deportation data ----------------------------------------------------------------------

REMOVAL_ORDER = ["Mexico", "Guatemala", "Honduras", "El Salvador", "Other LAC countries", "Non-LAC citizens"]


def _removals_public(d: pd.DataFrame) -> pd.DataFrame:
    p = d.pivot(index="fiscal_year", columns="group", values="removals").reindex(columns=REMOVAL_ORDER)
    p["Total"] = p.sum(axis=1)
    p["Partial year"] = d.groupby("fiscal_year").partial.first().map({True: "Yes", False: "No"})
    return p.reset_index().rename(columns={"fiscal_year": "Fiscal year"})


@chart("ddp_removals_fy",
       title="ICE removals by citizenship, fiscal years 2012–2026",
       source="Deportation Data Project, ICE records.",
       note="FY2026 is partial (to 11 March 2026) and hatched. Pandemic-era expulsions (FY2020–FY2022) are not removals.",
       public=_removals_public)
def ddp_removals_fy(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="fiscal_year", columns="group", values="removals").reindex(columns=REMOVAL_ORDER)
    partial = df.groupby("fiscal_year").partial.first()
    fig = go.Figure()
    for i, grp in enumerate(REMOVAL_ORDER):
        color = t["other"] if grp == "Non-LAC citizens" else C[i]
        # the partial fiscal year wears a 45-degree hatch (provisional), full color otherwise
        fig.add_trace(go.Bar(x=[f"FY{y}" for y in p.index], y=p[grp], name=grp,
                             marker=dict(color=color, line=dict(color=t["surface"], width=2), cornerradius=3,
                                         pattern=dict(shape=["/" if partial[y] else "" for y in p.index],
                                                      fgcolor=color, bgcolor=t["surface"], solidity=0.5, size=8)),
                             hovertemplate="%{y:,.0f}<extra>" + grp + "</extra>"))
    totals = p.sum(axis=1)
    for y in (2012, 2016, 2019, 2021, 2024, 2025):
        fig.add_annotation(x=f"FY{y}", y=totals[y], text=fmt_num(totals[y]), showarrow=False, yshift=12,
                           font=dict(color=t["text"], size=14))
    fig.add_annotation(x="FY2026", y=totals[2026], text="partial", showarrow=False, yshift=12,
                       font=dict(color=t["text2"], size=13))
    fig.update_layout(barmode="stack", bargap=0.3, hovermode="x unified",
                      xaxis=dict(tickfont=dict(size=13)),
                      yaxis=dict(**magnitude_axis(totals.max() * 1.12), title_text="Removals"))
    return fig


@chart("ddp_third_country",
       title="Removals to a third country, fiscal years 2012–2026",
       source="Deportation Data Project, ICE records.",
       note="A third country is not the person's own country. FY2026 is partial (to 11 March 2026).",
       public=lambda d: d.pivot(index="fiscal_year", columns="group", values="removals").reset_index().rename(
           columns={"fiscal_year": "Fiscal year"}))
def ddp_third_country(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    p = df.pivot(index="fiscal_year", columns="group", values="removals")
    fig = go.Figure()
    for i, grp in enumerate(["All citizenships", "LAC citizens"]):
        fig.add_trace(go.Scatter(x=[f"FY{y}" for y in p.index], y=p[grp], name=grp, mode="lines+markers",
                                 line=dict(color=C[i], width=3), marker=dict(size=9, color=C[i]),
                                 hovertemplate="%{y:,.0f}<extra>" + grp + "</extra>"))
        peak = p[grp].idxmax()
        fig.add_annotation(x=f"FY{peak}", y=p.loc[peak, grp], text=f"{p.loc[peak, grp]:,.0f}", showarrow=False,
                           yshift=16 if i == 0 else -18, font=dict(color=t["text"], size=14))
    fig.update_layout(hovermode="x unified", xaxis=dict(tickfont=dict(size=13)),
                      yaxis=dict(**magnitude_axis(p.max().max() * 1.15), title_text="Removals"))
    return fig


@chart("ddp_tps_backlog",
       title="TPS applications: received, decided and pending, 2015–2026",
       source="Deportation Data Project, USCIS records.",
       note="An application is not a person: renewals repeat. February 2026 is partial.",
       public=lambda d: d.assign(partial=d.partial.map({True: "Yes", False: "No"})).rename(columns={
           "month": "Month", "received": "Received", "decided": "Decided", "approved": "Approved",
           "denied": "Denied", "pending_stock": "Pending at month end", "partial": "Partial month"}))
def ddp_tps_backlog(df: pd.DataFrame, t: dict) -> go.Figure:
    C = t["colorway"]
    d = df.copy()
    d["date"] = pd.to_datetime(d.month + "-01")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08)
    fig.add_trace(go.Scatter(x=d.date, y=d.received, name="Received per month", mode="lines",
                             line=dict(color=C[0], width=2.5), hovertemplate="%{y:,.0f}<extra>Received</extra>"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=d.date, y=d.decided, name="Decided per month", mode="lines",
                             line=dict(color=C[1], width=2.5), hovertemplate="%{y:,.0f}<extra>Decided</extra>"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=d.date, y=d.pending_stock, name="Pending at month end", mode="lines",
                             line=dict(color=C[6], width=3), fill="tozeroy", fillcolor=rgba(C[6], 0.12),
                             hovertemplate="%{y:,.0f}<extra>Pending</extra>"), row=2, col=1)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(**magnitude_axis(d[["received", "decided"]].max().max() * 1.1), title_text="Per month",
                     row=1, col=1)
    fig.update_yaxes(**magnitude_axis(d.pending_stock.max() * 1.1), title_text="Pending", row=2, col=1)
    fig.update_xaxes(showgrid=False, dtick="M12", tickformat="%Y", row=2, col=1)
    return fig


# ---- rendering --------------------------------------------------------------------------------

def _fmt_cell(col: str, v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, (bool,)):
        return "Yes" if v else "No"
    if isinstance(v, (int, float)) or hasattr(v, "dtype"):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return html.escape(str(v))
        yearish = "year" in col.lower()
        if yearish and f == int(f):
            return str(int(f))
        if "(%)" in col or "rate" in col.lower():
            return f"{f:.1f}"
        return f"{f:,.0f}" if abs(f) >= 100 or f == int(f) else f"{f:,.2f}"
    return html.escape(str(v))


def _table_html(df: pd.DataFrame, cid: str, max_rows: int = 200) -> str:
    d = df.head(max_rows)
    head = "".join(f"<th scope=\"col\">{html.escape(str(c))}</th>" for c in d.columns)
    rows = "".join("<tr>" + "".join(f"<td>{_fmt_cell(str(c), r[c])}</td>" for c in d.columns) + "</tr>"
                   for _, r in d.iterrows())
    more = (f"<p class=\"chart__tablenote\">First {max_rows} of {len(df)} rows. The CSV has all of them.</p>"
            if len(df) > max_rows else "")
    return f"<div class=\"tablewrap\"><table class=\"data-table\"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>{more}"


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Whole-number float columns (counts after a pivot) become integers in the published CSV."""
    out = df.copy()
    for c in out.columns:
        s = out[c]
        if pd.api.types.is_float_dtype(s) and s.dropna().eq(s.dropna().round(0)).all():
            out[c] = s.round(0).astype("Int64")
    return out


def footnote(meta: dict) -> str:
    note = f"<strong>Note:</strong> {html.escape(meta['note'])} " if meta.get("note") else ""
    return f"{note}<strong>Source:</strong> {html.escape(meta['source'])}"


def build_figure(cid: str, df: pd.DataFrame, web: bool) -> go.Figure:
    meta = CHARTS[cid]
    fig = meta["build"](df, THEME[MODE])
    fig.update_layout(template=f"eco_{MODE}{'_web' if web else ''}")
    return fig


def write_fragment(cid: str, df: pd.DataFrame) -> str:
    meta = CHARTS[cid]
    fig = build_figure(cid, df, web=True)
    div = fig.to_html(full_html=False, include_plotlyjs=False, include_mathjax=False, div_id=f"plot-{cid}",
                      config=PLOTLY_CONFIG, default_width="100%", default_height="100%")
    public = _tidy(meta["public"](df))
    table = _tidy(meta["table"](df)) if meta["table"] else public
    frag = f"""<figure class="chart" id="fig-{cid}" data-chart>
  <div class="chart__frame">
    <figcaption class="chart__head"><h3 class="chart__title">{html.escape(meta['title'])}</h3></figcaption>
    <div class="chart__plot">{div}</div>
    <div class="chart__foot">
      <p class="chart__note">{footnote(meta)}</p>
      <p class="chart__links"><a href="#tbl-{cid}" class="js-open-table">Table</a><span aria-hidden="true"> · </span><a href="figures/{cid}.png" download>PNG</a><span aria-hidden="true"> · </span><a href="data/{cid}.csv" download>CSV</a></p>
    </div>
  </div>
  <details class="chart__table" id="tbl-{cid}"><summary>Table: {html.escape(meta['title'])}</summary>{_table_html(table, cid)}</details>
</figure>"""
    (CHARTS_OUT / f"{cid}.html").write_text(frag, encoding="utf-8")
    public.to_csv(CHARTS_OUT / f"{cid}.csv", index=False)
    return frag


def write_png(cid: str, df: pd.DataFrame) -> None:
    meta = CHARTS[cid]
    t = THEME[MODE]
    fig = build_figure(cid, df, web=False)
    top, bottom = 120, 150
    plot_h = PNG_H - top - bottom
    fig.update_layout(
        width=PNG_W, height=PNG_H, autosize=False,
        title=dict(text=f"<b>{html.escape(meta['title'])}</b>", x=0.03, xanchor="left", y=0.975, yanchor="top",
                   font=dict(size=28, color=t["text"])),
        margin=dict(t=top, b=bottom, l=80, r=max(80, fig.layout.margin.r or 0)))
    note = (f"<b>Note:</b> {html.escape(meta['note'])}<br>" if meta.get("note") else "") + \
        f"<b>Source:</b> {html.escape(meta['source'])}"
    fig.add_annotation(text=note, xref="paper", yref="paper", x=0, y=-(bottom - 18) / plot_h,
                       xanchor="left", yanchor="bottom", align="left", showarrow=False,
                       font=dict(size=15, color=t["text2"]))
    fig.write_image(str(FIG_OUT / f"{cid}.png"), width=PNG_W, height=PNG_H, scale=2)


def build_all(png: bool = True, only: list[str] | None = None) -> dict[str, str]:
    fragments = {}
    for cid in CHARTS:
        if only and cid not in only:
            continue
        df = pd.read_csv(DATA_OUT / f"{cid}.csv")
        fragments[cid] = write_fragment(cid, df)
        if png:
            write_png(cid, df)
        print(f"  [charts] {cid}: fragment + csv{' + png' if png else ''}")
    return fragments


if __name__ == "__main__":
    build_all()
