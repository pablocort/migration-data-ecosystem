"""Plotly templates for the site (dark, transparent) and for PNG export (dark/light).

Follows the dataviz method: thin marks, hairline solid gridlines, recessive axes,
legend always present for two or more series, text in text tokens (never in the
series color), categorical hues assigned in fixed order.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from .config import FONT, THEME


def make_template(mode: str, transparent: bool) -> go.layout.Template:
    t = THEME[mode]
    bg = "rgba(0,0,0,0)" if transparent else t["surface"]
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family=FONT, size=13, color=t["text"]),
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        colorway=t["colorway"],
        margin=dict(l=16, r=24, t=24, b=44),
        xaxis=dict(
            showgrid=False, zeroline=False, showline=True, linecolor=t["baseline"], linewidth=1,
            ticks="outside", tickcolor=t["baseline"], ticklen=4,
            tickfont=dict(color=t["text2"], size=12), title=dict(font=dict(color=t["text2"], size=12)),
            automargin=True,
        ),
        yaxis=dict(
            showgrid=True, gridcolor=t["grid"], gridwidth=1, zeroline=False, showline=False,
            ticks="", tickfont=dict(color=t["text2"], size=12), title=dict(font=dict(color=t["text2"], size=12)),
            automargin=True,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(color=t["text2"], size=12), itemsizing="constant",
            tracegroupgap=4, traceorder="normal",
        ),
        hoverlabel=dict(
            bgcolor=t["surface"] if mode == "dark" else "#ffffff", bordercolor=t["baseline"],
            font=dict(family=FONT, size=12, color=t["text"]),
        ),
        hovermode="closest",
        bargap=0.35,
        bargroupgap=0.08,
        colorscale=dict(sequential=[[0, "#cde2fb"], [0.5, "#3987e5"], [1, "#0d366b"]]),
    )
    tpl.data.bar = [go.Bar(marker=dict(line=dict(width=0)))]
    tpl.data.scatter = [go.Scatter(line=dict(width=2), marker=dict(size=9, line=dict(width=2, color=t["surface"])))]
    return tpl


def register() -> None:
    for mode in ("dark", "light"):
        pio.templates[f"eco_{mode}"] = make_template(mode, transparent=False)
        pio.templates[f"eco_{mode}_web"] = make_template(mode, transparent=True)


register()
