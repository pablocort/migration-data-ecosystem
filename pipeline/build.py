"""Build everything: extract -> charts -> site.

    py -3 -m pipeline.build              full build (reads the OneDrive source folders)
    py -3 -m pipeline.build --from-data  rebuild charts and site from the committed data/ CSVs
    py -3 -m pipeline.build --no-png     skip PNG export (faster)
    py -3 -m pipeline.build --site-only  only re-render the HTML pages
"""
from __future__ import annotations

import argparse
import sys
import time

from . import charts, coverage, extract_acs, extract_ddp, extract_eurostat, extract_global, extract_surveys, render_site


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-data", action="store_true", help="skip extraction, use data/*.csv")
    ap.add_argument("--no-png", action="store_true", help="skip PNG export")
    ap.add_argument("--site-only", action="store_true", help="only render the site from existing fragments")
    args = ap.parse_args(argv)

    t0 = time.time()
    if not args.site_only:
        if not args.from_data:
            for mod in (coverage, extract_acs, extract_eurostat, extract_global, extract_ddp, extract_surveys):
                print(f"== {mod.__name__}")
                mod.run()
        print("== charts")
        charts.build_all(png=not args.no_png)
    print("== site")
    render_site.render()
    print(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
