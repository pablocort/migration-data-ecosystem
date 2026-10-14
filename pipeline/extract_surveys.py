"""Household surveys: the IDB harmonized bank, Spain's EPA (HDMF) and the US surveys.

Inputs
  * running_survey.csv (IDB indicator pipeline): inventory of harmonized rounds by
    country, survey and year (availability flag, access right).
  * combined_df.csv (scl_data): person records from ten harmonized surveys
    2022-2023 with migrante_ci, edad_ci, condocup_ci and factor_ci. Only aggregates
    leave this script; the file itself is never copied into the repo.
  * comparadores.parquet (HDMF extract of Spain's EPA): indicators of natives and
    all migrants; epa_lac_2018_2024.csv: LAC-born persons in the EPA 2018-2024.
    Its `factor` is already the annual-average weight (quarterly factor / 4): summing
    it over the four quarters of a year gives the annual population (about 4.4 million
    LAC-born in 2024, in line with Eurostat and UN DESA). Do not divide it again.
    Rates are ratios, so they do not depend on this scale.
  * data/us_employment_lac_born.csv written by extract_acs.

Outputs (data/):
  svy_availability.csv                 row, family, year, survey
  svy_employment_migrants_natives.csv  country, iso3, survey, year, group, rate, n_unweighted
"""
from __future__ import annotations

import pandas as pd

from .config import DATA_OUT, EPA_EXTRACT, HDMF_COMPARADORES, SURVEY_COMBINED, SURVEY_INVENTORY
from .countries import BY_ISO3, sort_key

SOURCE_LABEL = {
    "ARG_2023s2_BID": ("ARG", "EPHC 2023 S2"),
    "CRI_2023m7_BID": ("CRI", "ENAHO 2023"),
    "COL_2023t3_BID": ("COL", "GEIH 2023 Q3"),
    "URY_2023a_BID": ("URY", "ECH 2023"),
    "CHL_2022m11_m12_m1_BID": ("CHL", "CASEN 2022"),
    "PRY_2023t4_BID": ("PRY", "EPHC 2023 Q4"),
    "PER_2023a_BID": ("PER", "ENAHO 2023"),
    "ECU_2023m12_BID": ("ECU", "ENEMDU 2023-12"),
    "DOM_2023t4_BID": ("DOM", "ENCFT 2023 Q4"),
    "MEX_2022m8_m12_BID": ("MEX", "ENIGH 2022"),
}


def availability() -> None:
    inv = pd.read_csv(SURVEY_INVENTORY)
    inv = inv[inv.availability.notna() & (inv.Pais != "Total")]
    rows = (inv.groupby(["Pais", "year"]).Encuesta
            .agg(lambda s: " / ".join(sorted(set(s)))).reset_index())
    rows = rows.rename(columns={"Pais": "iso3", "Encuesta": "survey"})
    rows["row"] = rows.iso3.map(lambda k: BY_ISO3[k].name if k in BY_ISO3 else k)
    rows["family"] = "IDB harmonized household surveys"
    rows = rows.sort_values(["iso3", "year"], key=lambda s: s.map(sort_key) if s.name == "iso3" else s)

    extra = []
    for y in [2014] + list(range(2018, 2026)):
        extra.append(dict(iso3="ESP", year=y, survey="EPA (INE), HDMF harmonization", row="Spain: EPA", family="Spain EPA (HDMF)"))
    for y in range(1994, 2026):
        extra.append(dict(iso3="USA", year=y, survey="CPS ASEC (IPUMS CPS)", row="United States: CPS ASEC", family="US surveys (IPUMS)"))
    for y in range(2001, 2025):
        extra.append(dict(iso3="USA", year=y, survey="ACS 1-year (IPUMS USA / PUMS)", row="United States: ACS", family="US surveys (IPUMS)"))
    out = pd.concat([rows, pd.DataFrame(extra)], ignore_index=True)[["row", "iso3", "family", "year", "survey"]]
    out.to_csv(DATA_OUT / "svy_availability.csv", index=False)
    n_rounds = len(inv)
    print(f"  [surveys] harmonized rounds in the inventory: {n_rounds} (expected 567: the 602 of the project "
          f"docs include 35 'Total' rows) in {len(rows)} country-years, {rows.year.min()}-{rows.year.max()}")
    assert n_rounds == 567


def employment() -> None:
    d = pd.read_csv(SURVEY_COMBINED, sep="|",
                    usecols=["migrante_ci", "edad_ci", "pais_c", "factor_ci", "condocup_ci", "source_file"])
    d = d[d.edad_ci.between(15, 64) & d.condocup_ci.isin(["Ocupado", "Desocupado", "Inactivo"]) & d.migrante_ci.notna()]
    d["w_emp"] = d.factor_ci * (d.condocup_ci == "Ocupado")
    g = (d.groupby(["source_file", "migrante_ci"])
         .agg(w=("factor_ci", "sum"), w_emp=("w_emp", "sum"), n_unweighted=("factor_ci", "size")).reset_index())
    g["rate"] = g.w_emp / g.w
    g["group"] = g.migrante_ci.map({0.0: "Native-born", 1.0: "Foreign-born"})
    g["iso3"] = g.source_file.map(lambda s: SOURCE_LABEL[s][0])
    g["survey"] = g.source_file.map(lambda s: SOURCE_LABEL[s][1])
    g["year"] = g.survey.str.extract(r"(\d{4})").astype(int)
    # keep countries where both groups exist and the migrant sample is usable
    ok = g.groupby("iso3").filter(lambda x: set(x.group) == {"Native-born", "Foreign-born"}
                                  and x.loc[x.group == "Foreign-born", "n_unweighted"].item() >= 100).iso3.unique()
    g = g[g.iso3.isin(ok)]
    g["country"] = g.iso3.map(lambda k: BY_ISO3[k].name)
    lac = g[["country", "iso3", "survey", "year", "group", "rate", "n_unweighted"]]

    # Spain: natives from the HDMF comparators, LAC-born from the EPA extract (2024, ages 16-64)
    comp = pd.read_parquet(HDMF_COMPARADORES)
    nat = comp[(comp.pais == "ESP") & (comp.periodo == "2024a") & (comp.grupo == "nativos") & (comp.indicador == "empleo")]
    epa = pd.read_csv(EPA_EXTRACT)
    e = epa[(epa.year == 2024) & epa.age.between(16, 64)]
    lac_born_rate = (e.factor * e.employed).sum() / e.factor.sum()
    spain = pd.DataFrame([
        dict(country="Spain", iso3="ESP", survey="EPA 2024 (HDMF)", year=2024, group="Native-born",
             rate=float(nat.valor.item()), n_unweighted=int(nat.n.item())),
        dict(country="Spain (LAC-born)", iso3="ESP", survey="EPA 2024 (HDMF special request)", year=2024,
             group="Foreign-born", rate=float(lac_born_rate), n_unweighted=int(len(e))),
    ])
    spain["country"] = "Spain"

    us = pd.read_csv(DATA_OUT / "us_employment_lac_born.csv")
    u = us[us.year == 2024].iloc[0]
    usa = pd.DataFrame([dict(country="United States (LAC-born only)", iso3="USA", survey="ACS 2024 PUMS", year=2024,
                             group="Foreign-born", rate=float(u.employment_rate_16_64), n_unweighted=int(u.n_unweighted))])

    out = pd.concat([lac, spain, usa], ignore_index=True)
    out.to_csv(DATA_OUT / "svy_employment_migrants_natives.csv", index=False)
    print("  [surveys] employment rate 15-64 by migrant status:")
    print(out.pivot_table(index=["country", "survey"], columns="group", values="rate").round(3).to_string())


def run() -> None:
    availability()
    employment()


if __name__ == "__main__":
    run()
