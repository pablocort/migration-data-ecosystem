"""United States: Census ACS 1-year PUMS cache of LAC-born residents, 2014-2024.

Input: ACS/data/census_pums/pums_lac_fb_<year>.csv.gz (YEAR, PWGTP, SEX, AGEP, ESR,
WKHP, CIT, POBP). Same records and weights as the IPUMS extract used by the ACS
project (PWGTP = PERWT), restricted to foreign-born persons born in LAC.

Outputs (data/):
  us_stock_by_country.csv      year, country, population, n_unweighted
  us_age_pyramid.csv           year, age_group, sex, share_pct, population
  us_employment_lac_born.csv   year, employment_rate_16_64, population_16_64, n_unweighted
"""
from __future__ import annotations

import pandas as pd

from .config import DATA_OUT, PUMS_DIR
from .countries import AGE_SHIFT_11, POBP_TO_NAME

AGE_BINS = list(range(0, 85, 5)) + [200]
AGE_LABELS = [f"{a}-{a + 4}" for a in range(0, 80, 5)] + ["80+"]


def load_pums() -> pd.DataFrame:
    frames = []
    for year in range(2014, 2025):
        f = PUMS_DIR / f"pums_lac_fb_{year}.csv.gz"
        df = pd.read_csv(f, usecols=["YEAR", "PWGTP", "SEX", "AGEP", "ESR", "CIT", "POBP"])
        frames.append(df)
    pums = pd.concat(frames, ignore_index=True)
    unknown = sorted(set(pums.POBP.unique()) - set(POBP_TO_NAME))
    if unknown:
        print(f"  [acs] POBP codes without a name (folded into 'Other LAC'): {unknown}")
    pums["country"] = pums.POBP.map(POBP_TO_NAME).fillna("Other LAC")
    return pums


def run() -> None:
    pums = load_pums()

    stock = (pums.groupby(["YEAR", "country"])
             .agg(population=("PWGTP", "sum"), n_unweighted=("PWGTP", "size"))
             .reset_index().rename(columns={"YEAR": "year"}))
    stock.to_csv(DATA_OUT / "us_stock_by_country.csv", index=False)

    sub = pums[pums.YEAR.isin([2014, 2024])].copy()
    sub["age_group"] = pd.cut(sub.AGEP, bins=AGE_BINS, labels=AGE_LABELS, right=False)
    sub["sex"] = sub.SEX.map({1: "Men", 2: "Women"})
    pyr = sub.groupby(["YEAR", "age_group", "sex"], observed=True).PWGTP.sum().reset_index()
    pyr = pyr.rename(columns={"YEAR": "year", "PWGTP": "population"})
    pyr["share_pct"] = pyr.population / pyr.groupby("year").population.transform("sum") * 100
    pyr.to_csv(DATA_OUT / "us_age_pyramid.csv", index=False)

    wa = pums[(pums.AGEP >= 16) & (pums.AGEP <= 64) & (pums.ESR > 0)].copy()
    wa["employed"] = wa.ESR.isin([1, 2, 4, 5]).astype(int)
    emp = (wa.assign(w_emp=wa.PWGTP * wa.employed)
           .groupby("YEAR").agg(w_emp=("w_emp", "sum"), population_16_64=("PWGTP", "sum"),
                                n_unweighted=("PWGTP", "size")).reset_index()
           .rename(columns={"YEAR": "year"}))
    emp["employment_rate_16_64"] = emp.w_emp / emp.population_16_64
    emp.drop(columns="w_emp").to_csv(DATA_OUT / "us_employment_lac_born.csv", index=False)

    # ---- checks against the ACS project's documented figures -----------------
    s24 = stock[stock.year == 2024].set_index("country").population
    s14 = stock[stock.year == 2014].set_index("country").population
    mx = s24["Mexico"]
    eleven_24 = s24.reindex(AGE_SHIFT_11).sum()
    eleven_14 = s14.reindex(AGE_SHIFT_11).sum()
    total_24 = s24.sum()
    print(f"  [acs] Mexico-born 2024: {mx:,.0f} (doc: 11,592,022)")
    print(f"  [acs] 11-country total 2014/2024: {eleven_14/1e6:.2f}M / {eleven_24/1e6:.2f}M (doc: 18.85M / 21.27M)")
    print(f"  [acs] all LAC-born 2024: {total_24/1e6:.2f}M (doc: 25.8M)")
    # The PUMS cache keeps the Census "foreign-born" universe (CIT 4 or 5: naturalized or
    # not a citizen). IPUMS birthplace counts also include people born abroad to US-citizen
    # parents (CIT 3), so they run ~4% higher for Mexico and the 11-country total. Both are
    # valid; the gap is a definition, documented on the site.
    print(f"  [acs] gap vs IPUMS birthplace counts (citizens at birth excluded here): "
          f"Mexico {mx/11_592_022-1:+.1%}, 11 countries {eleven_24/21.27e6-1:+.1%}")
    assert abs(mx - 11_592_022) / 11_592_022 < 0.06, "Mexico 2024 off by more than 6%"
    assert abs(eleven_24 - 21.27e6) / 21.27e6 < 0.06, "11-country 2024 total off by more than 6%"
    assert abs(total_24 - 25.8e6) / 25.8e6 < 0.03, "all-LAC 2024 total off by more than 3%"
    r24 = emp.set_index("year").employment_rate_16_64[2024]
    print(f"  [acs] employment rate 16-64, LAC-born, 2024: {r24:.3f} (doc, 11 countries: 0.737)")


if __name__ == "__main__":
    run()
