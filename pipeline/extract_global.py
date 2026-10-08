"""Global estimates held in the undesa folder: UN DESA IMS, FLown, UNHCR, KNOMAD.

Outputs (data/):
  gl_emigrants_destination.csv   year, destination, emigrants, share_pct
  gl_immigrant_stock_lac.csv     country, iso3, year, immigrants
  gl_displaced_lac_origin.csv    year, origin, refugees_asylum_seekers, oip
  gl_remittances_gdp.csv         iso3, country, year, remittances_musd, pct_gdp
"""
from __future__ import annotations

import json

import pandas as pd

from .config import DATA_OUT, FLOWN_EMIGRANTS, REMITTANCES_JSON, UNDESA_DATA_FULL, UNHCR_ORIGIN
from .countries import BY_ISO3, BY_UNDESA, IDB26

DEST_LABEL = {"dest_usa": "United States", "dest_lac": "Latin America and the Caribbean",
              "dest_spain": "Spain", "dest_others": "Other countries"}


def emigrants_destination() -> None:
    le = pd.read_csv(FLOWN_EMIGRANTS)
    g = le.groupby("year")[list(DEST_LABEL) + ["total_emigrants"]].sum()
    long = g[list(DEST_LABEL)].stack().reset_index()
    long.columns = ["year", "destination", "emigrants"]
    long["share_pct"] = long.emigrants / long.year.map(g.total_emigrants) * 100
    long["destination"] = long.destination.map(DEST_LABEL)
    long.to_csv(DATA_OUT / "gl_emigrants_destination.csv", index=False)
    t24 = g.loc[2024]
    print(f"  [global] LAC emigrants 2024: {t24.total_emigrants/1e6:.1f}M; USA {t24.dest_usa/t24.total_emigrants*100:.1f}% "
          f"(doc: 50.1M, 53.4%)")
    assert abs(t24.total_emigrants - 50.1e6) / 50.1e6 < 0.01


def immigrant_stock_lac() -> None:
    df = pd.read_excel(UNDESA_DATA_FULL, sheet_name="Table 1")
    dest_col, orig_col = df.columns[1], df.columns[5]
    years = [c for c in df.columns if isinstance(c, int)]
    sel = df[(df[orig_col] == "World") & (df[dest_col].isin(BY_UNDESA))]
    long = sel.melt(id_vars=[dest_col], value_vars=years, var_name="year", value_name="immigrants")
    long["country"] = long[dest_col].map(lambda n: BY_UNDESA[n].name)
    long["iso3"] = long[dest_col].map(lambda n: BY_UNDESA[n].iso3)
    long = long[long.iso3.isin([c.iso3 for c in IDB26])][["country", "iso3", "year", "immigrants"]]
    long["immigrants"] = long.immigrants.astype(float)
    long = long.sort_values(["country", "year"])
    long.to_csv(DATA_OUT / "gl_immigrant_stock_lac.csv", index=False)
    s = long.groupby("year").immigrants.sum()
    print(f"  [global] immigrants in the 26 IDB countries: 1990 {s[1990]/1e6:.2f}M, 2024 {s[2024]/1e6:.2f}M (doc: 16.56M in 2024)")
    assert abs(s[2024] - 16.56e6) / 16.56e6 < 0.02


def displaced_lac_origin() -> None:
    a = pd.read_csv(UNHCR_ORIGIN)
    g = a.groupby(["year", "coo_iso"])[["refugees", "asylum_seekers", "oip"]].sum().reset_index()
    g["refugees_asylum_seekers"] = g.refugees + g.asylum_seekers
    top = g[g.year == 2024].sort_values("refugees_asylum_seekers", ascending=False).coo_iso.head(5).tolist()
    g["origin"] = g.coo_iso.where(g.coo_iso.isin(top), "OTHER")
    out = g.groupby(["year", "origin"])[["refugees_asylum_seekers", "oip"]].sum().reset_index()
    out["origin"] = out.origin.map(lambda k: BY_ISO3[k].name if k in BY_ISO3 else "Other LAC countries")
    out.to_csv(DATA_OUT / "gl_displaced_lac_origin.csv", index=False)
    v = out[(out.year == 2024) & (out.origin == "Venezuela")].iloc[0]
    print(f"  [global] Venezuela 2024: refugees+asylum-seekers {v.refugees_asylum_seekers:,.0f}, other people in need of "
          f"international protection {v.oip:,.0f}")


def remittances_gdp() -> None:
    dj = pd.DataFrame(json.load(open(REMITTANCES_JSON, encoding="utf-8")))
    for c in ["value", "remittance_percent_pib"]:
        dj[c] = pd.to_numeric(dj[c], errors="coerce")
    dj = dj[dj.iso3.isin(BY_ISO3) & (dj.year == 2024)].dropna(subset=["remittance_percent_pib"])
    out = dj.rename(columns={"value": "remittances_musd", "remittance_percent_pib": "pct_gdp"})
    out["country"] = out.iso3.map(lambda k: BY_ISO3[k].name)
    out = out[["iso3", "country", "year", "remittances_musd", "pct_gdp"]].sort_values("pct_gdp", ascending=False)
    out.to_csv(DATA_OUT / "gl_remittances_gdp.csv", index=False)
    print(f"  [global] remittances % GDP 2024, top 3: {out.head(3)[['iso3', 'pct_gdp']].values.tolist()}")


def run() -> None:
    emigrants_destination()
    immigrant_stock_lac()
    displaced_lac_origin()
    remittances_gdp()


if __name__ == "__main__":
    run()
