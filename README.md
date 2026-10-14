# Migration Data Ecosystem

A static site that profiles the data sources used to study migration from Latin America and the
Caribbean (LAC): what each source gives, how far it reaches, where it breaks, and one or two charts per
topic. Built for a team presentation; published at
**https://pablocort.github.io/migration-data-ecosystem/**.

Five source families are profiled:

| # | Page | Sources |
|---|---|---|
| 01 | United States | IPUMS USA (census and ACS microdata), Census ACS PUMS, IPUMS CPS |
| 02 | Europe | Eurostat migration, permit, asylum and enforcement statistics; IME consular records |
| 03 | Household surveys | IDB harmonized household surveys (26 countries), Spain's EPA via the HDMF project, the US surveys |
| 04 | Global estimates | UN DESA International Migrant Stock, FLown annual bilateral estimates (Azose and Raftery via Gaskin and Abel), UNHCR Refugee Data Finder, UN World Population Prospects, KNOMAD and central-bank remittances |
| 05 | Deportation data | Deportation Data Project: ICE removals, arrests and detentions; USCIS TPS and DACA applications; CBP encounters |

## How it is built

```
pipeline/
  config.py            paths (MIG_DATA_ROOT env var), validated chart palette, constants
  countries.py         LAC country crosswalk (ISO codes, Census POBP codes, UN DESA and ICE names)
  theme.py             Plotly templates (light, projection-sized type) for the site and the PNG export
  coverage.py          hand-maintained time-coverage inventory for the index timeline
  extract_*.py         one extractor per source family -> data/<chart id>.csv (small aggregates)
  charts.py            chart builders -> charts/<id>.html fragments, charts/<id>.csv (public, readable
                       headers) and figures/<id>.png
  render_site.py       Jinja2 templates + site/content/*.yml -> docs/
  check_public.py      fails the build if a published page or CSV header carries internal references
                       (variable or dataset codes, file or pipeline words); warns on sentences over 25 words
  build.py             orchestrates everything
site/
  templates/           base.html, index.html, page.html
  content/             one YAML file per page (profiles, charts, traps, links)
  static/              styles.css, site.js, favicon.svg
data/                  aggregated tables behind each chart (committed; reproducible from the sources)
charts/                generated Plotly fragments (committed)
figures/               generated PNGs for slides (not committed; the published copy is docs/figures)
docs/                  rendered site served by GitHub Pages (committed)
```

The site is built to be projected. It uses a light theme in which every readable text clears 7:1 contrast.
Each chart card (title, plot and footnote) fits one screen at 1280×720 and larger. Charts have no
subtitles: what a reader must know goes in the footnote. Press N or P on a page to jump to the next or
previous chart or section.

Charts follow a documented data-visualization method: forms chosen by the data's job, a categorical palette
validated for colour-vision deficiency and contrast against a white surface, thin marks, hairline grids,
a legend for every multi-series chart, and a table view plus CSV for every chart.

The presentation script lives in `presentacion/`, which is excluded from git.

### Rebuild

Requirements: Python 3.12+ and the packages in `requirements.txt` (`py -3 -m pip install -r requirements.txt`).
PNG export uses kaleido, which needs Chrome or Chromium installed.

```
py -3 -m pipeline.build              # extract from the source folders, build charts, render the site
py -3 -m pipeline.build --from-data  # rebuild charts and site from the committed data/ CSVs only
py -3 -m pipeline.build --no-png     # skip PNG export
py -3 -m pipeline.build --site-only  # re-render the HTML only
```

The extractors read the source projects' folders (ACS, eurostat, undesa, ddp, scl_data and the survey
inventory), which are not part of this repository. Set `MIG_DATA_ROOT` to the folder that contains them;
by default it is the parent of the project folder. Every extractor checks the headline numbers against the
documentation of the source project before writing a table.

## What is and is not published

Only small aggregated tables (country by year, and similar) are committed. No microdata, no record-level
enforcement data, no internal documents and no API keys are part of the repository. Each page carries the
citation its source requires.

## Citations

- Ruggles, S. et al. IPUMS USA: Version 16.0 [dataset]. Minneapolis, MN: IPUMS, 2025. Flood, S. et al. IPUMS CPS [dataset].
- US Census Bureau, American Community Survey 1-Year Public Use Microdata Sample, 2014–2024.
- Eurostat, migration and asylum statistics (migr_* datasets), extracted September 2026, CC BY 4.0.
- Inter-American Development Bank, Social Sector, Harmonized Household Surveys of Latin America and the Caribbean.
- Instituto Nacional de Estadística (Spain), Encuesta de Población Activa, harmonized by the IDB project How do Migrants Fare in LAC.
- United Nations, Department of Economic and Social Affairs, Population Division, International Migrant Stock 2024; World Population Prospects 2024.
- Azose, J. and Raftery, A. (2019) FLown estimates, accessed via Gaskin, T. and Abel, G. (2025), Deep learning four decades of human migration, arXiv 2506.22821.
- UNHCR Refugee Data Finder.
- KNOMAD / World Bank, remittance inflows.
- Deportation Data Project, deportationdata.org: ICE, USCIS and CBP records obtained under FOIA.

Site design adapted from the navy and ivory system of tomaspieroni-cloud.github.io. Fonts: Fraunces, Manrope
and IBM Plex Mono (SIL Open Font License) via Google Fonts.
