"""Paths, palette and shared constants for the Migration Data Ecosystem pipeline.

Source folders are read-only inputs that live outside this repo (OneDrive).
Set MIG_DATA_ROOT to point at the folder that contains ACS/, eurostat/, undesa/,
ddp/, scl_data/ and GitHub_2/; by default it is the parent of this project.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("MIG_DATA_ROOT", ROOT.parent))

# ---- inputs (never written) -------------------------------------------------
ACS_DIR = DATA_ROOT / "ACS"
PUMS_DIR = ACS_DIR / "data" / "census_pums"
ACS_RR2 = ACS_DIR / "output" / "Reporte de Remesas - Parte 2"
EPA_EXTRACT = ACS_RR2 / "datos" / "espana" / "epa_lac_2018_2024.csv"

EUROSTAT_DIR = DATA_ROOT / "eurostat"
EUROSTAT_PARQUET = EUROSTAT_DIR / "data" / "derived" / "eurostat"
HDMF_COMPARADORES = EUROSTAT_DIR / "data" / "derived" / "hdmf" / "comparadores.parquet"

UNDESA_DIR = DATA_ROOT / "undesa"
UNDESA_DATA_FULL = UNDESA_DIR / "data" / "intermediate" / "data_full.xlsx"
FLOWN_EMIGRANTS = UNDESA_DIR / "outputs" / "tables" / "emigrants" / "lac_emigrants_by_destination.csv"
UNHCR_ORIGIN = UNDESA_DIR / "data" / "raw" / "acnur" / "acnur_bilateral_lac_origin.csv"
REMITTANCES_JSON = UNDESA_DIR / "data" / "raw" / "remittances" / "remittance-data.json"

DDP_DIR = DATA_ROOT / "ddp" / "update 03-31"
DDP_TOTAL = DDP_DIR / "tabla_deport_total_valores.csv"
DDP_LAC = DDP_DIR / "tabla_deport_lac_valores.csv"
DDP_THIRD = DDP_DIR / "tabla_tercpais_valores.csv"
DDP_TPS = DDP_DIR / "outputs" / "tabla_uscis_mes" / "tps_mensual_total.csv"

SURVEY_INVENTORY = DATA_ROOT / "GitHub_2" / "calculo_indicators_R" / "Inputs" / "running_survey.csv"
SURVEY_COMBINED = DATA_ROOT / "scl_data" / "combined_df.csv"

# ---- outputs (inside the repo) ----------------------------------------------
DATA_OUT = ROOT / "data"
CHARTS_OUT = ROOT / "charts"
FIG_OUT = ROOT / "figures"
SITE_SRC = ROOT / "site"
SITE_OUT = ROOT / "docs"

for _d in (DATA_OUT, CHARTS_OUT, FIG_OUT / "dark", FIG_OUT / "light"):
    _d.mkdir(parents=True, exist_ok=True)

# ---- chart palette (validated with the dataviz six-checks validator) --------
# Categorical slots, fixed order, never cycled. Dark steps validated against the
# site's chart surface #0F252E (all PASS, adjacent and first-3 all-pairs); light
# steps validated against #fcfcfb (PASS; three slots need direct labels or the
# table view as contrast relief, which every chart ships).
CAT_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
CAT_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE_RAMP = {
    100: "#cde2fb", 150: "#b7d3f6", 200: "#9ec5f4", 250: "#86b6ef", 300: "#6da7ec",
    350: "#5598e7", 400: "#3987e5", 450: "#2a78d6", 500: "#256abf", 550: "#1c5cab",
    600: "#184f95", 650: "#104281", 700: "#0d366b",
}

THEME = {
    "dark": dict(
        surface="#0F252E", page="#0B1B24", text="#F8F7F1", text2="#C5CFD2", muted="#8FA1A8",
        grid="#1E3640", baseline="#2E4A55", other="#6B7E86", earlier=BLUE_RAMP[250],
        colorway=CAT_DARK,
    ),
    "light": dict(
        surface="#fcfcfb", page="#f9f9f7", text="#0b0b0b", text2="#52514e", muted="#898781",
        grid="#e1e0d9", baseline="#c3c2b7", other="#9a9892", earlier=BLUE_RAMP[250],
        colorway=CAT_LIGHT,
    ),
}
FONT = "Manrope, 'Segoe UI', Arial, sans-serif"

SITE_URL = "https://pablocort.github.io/migration-data-ecosystem/"
REPO_URL = "https://github.com/pablocort/migration-data-ecosystem"
