"""Render the static site: site/content/*.yml + site/templates -> docs/ (GitHub Pages)."""
from __future__ import annotations

import shutil
from datetime import date

import yaml
from jinja2 import Environment, FileSystemLoader

from .charts import CHARTS
from .config import CHARTS_OUT, DATA_OUT, FIG_OUT, REPO_URL, SITE_OUT, SITE_SRC, SITE_URL

NAV = [
    ("index.html", "Overview", "Overview"),
    ("us-acs.html", "01 United States", "01"),
    ("europe-eurostat.html", "02 Europe", "02"),
    ("household-surveys.html", "03 Surveys", "03"),
    ("global-estimates.html", "04 Global estimates", "04"),
    ("deportation-data.html", "05 Deportation data", "05"),
    ("concepts.html", "Concepts", "Concepts"),
]


def _normalize(node):
    """YAML turns an unquoted list item such as 'Detention: how long ...' into a one-key
    mapping. Fold those back into the sentence the author wrote."""
    if isinstance(node, list):
        out = []
        for v in node:
            if isinstance(v, dict) and len(v) == 1:
                k, val = next(iter(v.items()))
                if isinstance(k, str) and isinstance(val, str):
                    out.append(f"{k}: {val}")
                    continue
            out.append(_normalize(v))
        return out
    if isinstance(node, dict):
        return {k: _normalize(v) for k, v in node.items()}
    return node


def load_content() -> dict:
    content = {}
    for f in sorted((SITE_SRC / "content").glob("*.yml")):
        content[f.stem] = _normalize(yaml.safe_load(f.read_text(encoding="utf-8")))
    return content


def load_fragments() -> dict[str, str]:
    return {f.stem: f.read_text(encoding="utf-8") for f in CHARTS_OUT.glob("*.html")}


def render() -> None:
    env = Environment(loader=FileSystemLoader(str(SITE_SRC / "templates")), autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    content = load_content()
    fragments = load_fragments()
    pages = content["pages"]
    common = dict(nav=NAV, site_url=SITE_URL, repo_url=REPO_URL, built=date.today().isoformat(),
                  charts=fragments, chart_meta=CHARTS, pages=pages)

    SITE_OUT.mkdir(exist_ok=True)
    (SITE_OUT / ".nojekyll").write_text("", encoding="utf-8")

    index_tpl = env.get_template("index.html")
    (SITE_OUT / "index.html").write_text(index_tpl.render(page=content["index"], **common), encoding="utf-8")

    page_tpl = env.get_template("page.html")
    for slug in pages:
        page = content[slug.replace("-", "_")] if slug.replace("-", "_") in content else content[slug]
        (SITE_OUT / f"{slug}.html").write_text(page_tpl.render(page=page, slug=slug, **common), encoding="utf-8")

    # copy over existing files instead of deleting folders: OneDrive holds locks on directories
    shutil.copytree(SITE_SRC / "static", SITE_OUT / "assets", dirs_exist_ok=True)
    shutil.copytree(FIG_OUT, SITE_OUT / "figures", dirs_exist_ok=True)
    (SITE_OUT / "data").mkdir(exist_ok=True)
    for f in DATA_OUT.glob("*.csv"):
        shutil.copy(f, SITE_OUT / "data" / f.name)
    print(f"  [site] rendered {1 + len(pages)} pages into {SITE_OUT}")


if __name__ == "__main__":
    render()
