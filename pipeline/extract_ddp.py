"""Deportation Data Project: tables already built by the ddp project (FY2023 deduplicated).

Outputs (data/):
  ddp_removals_fy.csv     fiscal_year, group, removals, partial
  ddp_third_country.csv   fiscal_year, group, removals
  ddp_tps_backlog.csv     month, received, decided, approved, denied, pending_stock, partial
"""
from __future__ import annotations

import pandas as pd

from .config import DATA_OUT, DDP_LAC, DDP_THIRD, DDP_TOTAL, DDP_TPS

NAMED = {"MEXICO": "Mexico", "GUATEMALA": "Guatemala", "HONDURAS": "Honduras", "EL SALVADOR": "El Salvador"}
LAST_FY = 2026  # partial: data cut 11 March 2026


def _wide_to_long(df: pd.DataFrame, id_col: str) -> pd.DataFrame:
    df = df.rename(columns={df.columns[0]: id_col})
    years = [c for c in df.columns if str(c).isdigit()]
    long = df.melt(id_vars=[id_col], value_vars=years, var_name="fiscal_year", value_name="removals")
    long["fiscal_year"] = long.fiscal_year.astype(int)
    return long


def removals() -> None:
    lac = _wide_to_long(pd.read_csv(DDP_LAC, encoding="utf-8"), "country")
    tot = _wide_to_long(pd.read_csv(DDP_TOTAL, encoding="utf-8"), "group")
    tot_w = tot.pivot(index="fiscal_year", columns="group", values="removals")
    named = lac[lac.country.isin(NAMED)].assign(group=lambda d: d.country.map(NAMED))
    lac_total = lac.groupby("fiscal_year").removals.sum()
    rows = [named[["fiscal_year", "group", "removals"]]]
    other_lac = (lac_total - named.groupby("fiscal_year").removals.sum()).reset_index().assign(group="Other LAC countries")
    non_lac = (tot_w["Total"] - tot_w["LAC"]).reset_index().rename(columns={0: "removals"}).assign(group="Non-LAC citizens")
    non_lac.columns = ["fiscal_year", "removals", "group"]
    rows += [other_lac, non_lac]
    out = pd.concat(rows, ignore_index=True)
    out["partial"] = out.fiscal_year == LAST_FY
    out = out.sort_values(["fiscal_year", "group"])
    out.to_csv(DATA_OUT / "ddp_removals_fy.csv", index=False)
    chk = out.groupby("fiscal_year").removals.sum()
    print(f"  [ddp] ICE removals FY2012 {chk[2012]:,.0f} / FY2021 {chk[2021]:,.0f} / FY2025 {chk[2025]:,.0f} "
          f"(doc: 406,654 / 56,794 / 367,407)")
    assert chk[2012] == 406_654 and chk[2025] == 367_407
    lac_share_25 = tot_w.loc[2025, "LAC"] / tot_w.loc[2025, "Total"]
    print(f"  [ddp] LAC share of removals FY2025: {lac_share_25:.1%}")


def third_country() -> None:
    t = pd.read_csv(DDP_THIRD, encoding="utf-8")
    years = [c for c in t.columns if str(c).isdigit()]
    all_ = t[(t.Grupo == "Total")][years].iloc[0]
    lac = t[t.Grupo == "LAC"][years].sum()
    out = pd.DataFrame({"fiscal_year": [int(y) for y in years],
                        "All citizenships": all_.values, "LAC citizens": lac.values})
    out = out.melt(id_vars="fiscal_year", var_name="group", value_name="removals")
    out.to_csv(DATA_OUT / "ddp_third_country.csv", index=False)
    print(f"  [ddp] third-country removals, all citizenships: 2023 {all_['2023']:,.0f}, 2024 {all_['2024']:,.0f}, "
          f"2025 {all_['2025']:,.0f} (doc: 4,505 / 30,839 / 36,696)")
    assert int(all_["2025"]) == 36_696


def tps() -> None:
    t = pd.read_csv(DDP_TPS)
    t = t[t.mes >= "2015-01"]
    out = t.rename(columns={"mes": "month", "solicitudes": "received", "decisiones": "decided",
                            "aprobadas": "approved", "denegadas": "denied", "pendientes_stock": "pending_stock",
                            "parcial": "partial"})
    out = out[["month", "received", "decided", "approved", "denied", "pending_stock", "partial"]]
    out.to_csv(DATA_OUT / "ddp_tps_backlog.csv", index=False)
    s = out.set_index("month").pending_stock
    print(f"  [ddp] TPS pending stock: 2024-12 {s['2024-12']:,.0f}, 2026-02 {s['2026-02']:,.0f} (doc: 457,921 / 1,162,121)")
    assert int(s["2026-02"]) == 1_162_121


def run() -> None:
    removals()
    third_country()
    tps()


if __name__ == "__main__":
    run()
