"""Country crosswalk shared by every extractor.

Columns: iso3, iso2, name, subregion, idb26 (IDB borrowing member), pobp (Census
ACS PUMS place-of-birth code), undesa (name as written in UN DESA IMS 2024),
ice (citizenship spelling in the ICE FOIA tables).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    iso3: str
    iso2: str
    name: str
    subregion: str
    idb26: bool
    pobp: int | None
    undesa: str
    ice: str


_ROWS = [
    ("ATG", "AG", "Antigua and Barbuda", "Caribbean", False, 321, "Antigua and Barbuda", "ANTIGUA-BARBUDA"),
    ("ARG", "AR", "Argentina", "South America", True, 360, "Argentina", "ARGENTINA"),
    ("BHS", "BS", "Bahamas", "Caribbean", True, 323, "Bahamas", "BAHAMAS"),
    ("BRB", "BB", "Barbados", "Caribbean", True, 324, "Barbados", "BARBADOS"),
    ("BLZ", "BZ", "Belize", "Central America", True, 310, "Belize", "BELIZE"),
    ("BOL", "BO", "Bolivia", "South America", True, 361, "Bolivia (Plurinational State of)", "BOLIVIA"),
    ("BRA", "BR", "Brazil", "South America", True, 362, "Brazil", "BRAZIL"),
    ("CHL", "CL", "Chile", "South America", True, 363, "Chile", "CHILE"),
    ("COL", "CO", "Colombia", "South America", True, 364, "Colombia", "COLOMBIA"),
    ("CRI", "CR", "Costa Rica", "Central America", True, 311, "Costa Rica", "COSTA RICA"),
    ("CUB", "CU", "Cuba", "Caribbean", False, 327, "Cuba", "CUBA"),
    ("DMA", "DM", "Dominica", "Caribbean", False, 328, "Dominica", "DOMINICA"),
    ("DOM", "DO", "Dominican Republic", "Caribbean", True, 329, "Dominican Republic", "DOMINICAN REPUBLIC"),
    ("ECU", "EC", "Ecuador", "South America", True, 365, "Ecuador", "ECUADOR"),
    ("SLV", "SV", "El Salvador", "Central America", True, 312, "El Salvador", "EL SALVADOR"),
    ("GRD", "GD", "Grenada", "Caribbean", False, 330, "Grenada", "GRENADA"),
    ("GTM", "GT", "Guatemala", "Central America", True, 313, "Guatemala", "GUATEMALA"),
    ("GUY", "GY", "Guyana", "South America", True, 368, "Guyana", "GUYANA"),
    ("HTI", "HT", "Haiti", "Caribbean", True, 332, "Haiti", "HAITI"),
    ("HND", "HN", "Honduras", "Central America", True, 314, "Honduras", "HONDURAS"),
    ("JAM", "JM", "Jamaica", "Caribbean", True, 333, "Jamaica", "JAMAICA"),
    ("MEX", "MX", "Mexico", "Central America", True, 303, "Mexico", "MEXICO"),
    ("NIC", "NI", "Nicaragua", "Central America", True, 315, "Nicaragua", "NICARAGUA"),
    ("PAN", "PA", "Panama", "Central America", True, 316, "Panama", "PANAMA"),
    ("PRY", "PY", "Paraguay", "South America", True, 369, "Paraguay", "PARAGUAY"),
    ("PER", "PE", "Peru", "South America", True, 370, "Peru", "PERU"),
    ("KNA", "KN", "Saint Kitts and Nevis", "Caribbean", False, 338, "Saint Kitts and Nevis", "ST. KITTS-NEVIS"),
    ("LCA", "LC", "Saint Lucia", "Caribbean", False, 339, "Saint Lucia", "ST. LUCIA"),
    ("VCT", "VC", "Saint Vincent and the Grenadines", "Caribbean", False, 340, "Saint Vincent and the Grenadines", "ST. VINCENT-GRENADINES"),
    ("SUR", "SR", "Suriname", "South America", True, None, "Suriname", "SURINAME"),
    ("TTO", "TT", "Trinidad and Tobago", "Caribbean", True, 341, "Trinidad and Tobago", "TRINIDAD AND TOBAGO"),
    ("URY", "UY", "Uruguay", "South America", True, 372, "Uruguay", "URUGUAY"),
    ("VEN", "VE", "Venezuela", "South America", True, 373, "Venezuela (Bolivarian Republic of)", "VENEZUELA"),
]

COUNTRIES: list[Country] = [Country(*r) for r in _ROWS]
LAC33 = COUNTRIES
IDB26 = [c for c in COUNTRIES if c.idb26]

BY_ISO3 = {c.iso3: c for c in COUNTRIES}
BY_ISO2 = {c.iso2: c for c in COUNTRIES}
BY_UNDESA = {c.undesa: c for c in COUNTRIES}
BY_ICE = {c.ice: c for c in COUNTRIES}
LAC_ISO2 = [c.iso2 for c in COUNTRIES]
LAC_ISO3 = [c.iso3 for c in COUNTRIES]

# Census ACS PUMS place-of-birth codes: named countries plus the residual buckets
# that the PUMS cache keeps (it filters POBP 303, 310-316, 320-344, 360-374).
POBP_TO_NAME = {c.pobp: c.name for c in COUNTRIES if c.pobp is not None}
POBP_TO_NAME.update({343: "Other Caribbean", 344: "Other Caribbean", 374: "Other South America"})

# The 11 countries of the ACS project's "Age Shift" analysis (for cross-checks).
AGE_SHIFT_11 = ["Mexico", "El Salvador", "Guatemala", "Honduras", "Nicaragua", "Panama",
                "Dominican Republic", "Haiti", "Jamaica", "Colombia", "Ecuador"]

SUBREGION_ORDER = ["Central America", "Caribbean", "South America"]


def sort_key(name_or_iso3: str) -> tuple:
    c = BY_ISO3.get(name_or_iso3)
    if c is None:
        c = next((x for x in COUNTRIES if x.name == name_or_iso3), None)
    if c is None:
        return (99, name_or_iso3)
    return (SUBREGION_ORDER.index(c.subregion), c.name)
