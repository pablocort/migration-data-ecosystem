"""Europe: Eurostat migration statistics (tidy parquet cache of the eurostat project).

Rules applied everywhere (from the project's data guide):
  * geo aggregates (EU27_2020, EA20...) are excluded: keep two-letter reporting countries;
  * either the TOTAL of a dimension or its components, never both;
  * OBS_FLAG is kept in the extracts.

Outputs (data/):
  eu_lac_born_2024.csv          country, iso2, host, host_name, population
  eu_first_permits_reason.csv   year, reason, permits, n_reporting
  eu_asylum_first_time.csv      year, origin, applicants
"""
from __future__ import annotations

import polars as pl

from .config import DATA_OUT, EUROSTAT_PARQUET
from .countries import BY_ISO2, LAC_ISO2

GEO_COUNTRY = pl.col("geo").str.contains(r"^[A-Z]{2}$")
REASON_LABEL = {"FAM": "Family", "EDUC": "Education", "EMP": "Employment", "OTH": "Other reasons"}


def _scan(code: str) -> pl.LazyFrame:
    return pl.scan_parquet(EUROSTAT_PARQUET / f"{code}.parquet")


def lac_born_2024() -> None:
    df = (_scan("migr_pop3ctb")
          .filter(pl.col("c_birth").is_in(LAC_ISO2), pl.col("age") == "TOTAL", pl.col("sex") == "T",
                  GEO_COUNTRY, pl.col("year") == 2024, pl.col("OBS_VALUE").is_not_null())
          .select("c_birth", "geo", "geo_label", "OBS_VALUE", "OBS_FLAG")
          .collect().to_pandas())
    df["country"] = df.c_birth.map(lambda k: BY_ISO2[k].name)
    totals_by_host = df.groupby("geo").OBS_VALUE.sum().sort_values(ascending=False)
    top_hosts = list(totals_by_host.index[:5])
    df["host"] = df.geo.where(df.geo.isin(top_hosts), "OTHER")
    names = dict(zip(df.geo, df.geo_label))
    names["OTHER"] = "Other reporting countries"
    out = (df.groupby(["country", "c_birth", "host"]).OBS_VALUE.sum().reset_index()
           .rename(columns={"c_birth": "iso2", "OBS_VALUE": "population"}))
    out["host_name"] = out.host.map(names)
    out = out[out.population > 0]
    out.to_csv(DATA_OUT / "eu_lac_born_2024.csv", index=False)
    co = out[out.country == "Colombia"].population.sum()
    ve = out[out.country == "Venezuela"].population.sum()
    print(f"  [eurostat] born in Colombia / Venezuela, 2024, reporting countries: {co:,.0f} / {ve:,.0f} (doc: ~964k / ~690k)")
    assert abs(co - 964_000) / 964_000 < 0.03
    reporting = sorted(df.geo.unique())
    missing = [g for g in ("FR", "DE") if g not in reporting]
    print(f"  [eurostat] {len(reporting)} reporting countries; missing among big hosts: {missing}")


def first_permits_reason() -> None:
    lf = (_scan("migr_resfirst")
          .filter(pl.col("citizen").is_in(LAC_ISO2), pl.col("duration") == "TOTAL",
                  pl.col("reason").is_in(list(REASON_LABEL)), GEO_COUNTRY,
                  pl.col("year").is_between(2010, 2025), pl.col("OBS_VALUE").is_not_null()))
    out = (lf.group_by("year", "reason")
             .agg(pl.col("OBS_VALUE").sum().alias("permits"), pl.col("geo").n_unique().alias("n_reporting"))
             .collect().to_pandas().sort_values(["year", "reason"]))
    out["reason"] = out.reason.map(REASON_LABEL)
    out.to_csv(DATA_OUT / "eu_first_permits_reason.csv", index=False)
    mx = (_scan("migr_resfirst")
          .filter(pl.col("citizen") == "MX", pl.col("duration") == "TOTAL", pl.col("reason") == "EDUC",
                  GEO_COUNTRY, pl.col("year") == 2025)
          .select(pl.col("OBS_VALUE").sum()).collect().item())
    print(f"  [eurostat] first permits, Mexican citizens, education, 2025: {mx:,.0f} (doc: 12,460)")
    assert mx == 12_460
    tot25 = out[out.year == 2025].permits.sum()
    print(f"  [eurostat] first permits to LAC citizens, 2025, all reasons: {tot25:,.0f}")


def asylum_first_time() -> None:
    df = (_scan("migr_asyappctza")
          .filter(pl.col("citizen").is_in(LAC_ISO2), pl.col("applicant") == "FRST", pl.col("sex") == "T",
                  pl.col("age") == "TOTAL", GEO_COUNTRY, pl.col("year") >= 2008, pl.col("OBS_VALUE").is_not_null())
          .group_by("year", "citizen").agg(pl.col("OBS_VALUE").sum().alias("applicants"))
          .collect().to_pandas())
    df["country"] = df.citizen.map(lambda k: BY_ISO2[k].name)
    top = df[df.year == 2025].sort_values("applicants", ascending=False).country.head(5).tolist()
    df["origin"] = df.country.where(df.country.isin(top), "Other LAC countries")
    out = df.groupby(["year", "origin"]).applicants.sum().reset_index().sort_values(["year", "origin"])
    out.to_csv(DATA_OUT / "eu_asylum_first_time.csv", index=False)
    ve = out[(out.year == 2025) & (out.origin == "Venezuela")].applicants.item()
    print(f"  [eurostat] first-time asylum applicants, Venezuelan citizens, 2025: {ve:,.0f} (doc: 89,790)")
    assert ve == 89_790


def run() -> None:
    lac_born_2024()
    first_permits_reason()
    asylum_first_time()


if __name__ == "__main__":
    run()
