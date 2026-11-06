"""Deterministic and state-configurable unit conversions for Indian property area measurements into standard square feet."""

import re
from typing import Any, Dict, Optional, Tuple
from app.normalization.models import AreaUnit

# Exact SI and national standard conversion factors to Square Feet (sqft)
# 1 metre = 3.280839895013123 ft -> 1 sq metre = 10.763910416709722 sqft
SQM_TO_SQFT = 10.763910416709722
SQYD_TO_SQFT = 9.0
ACRE_TO_SQFT = 43560.0
HECTARE_TO_SQFT = 107639.10416709722
GROUND_TO_SQFT = 2400.0        # Standard Tamil Nadu (1 Ground = 2400 sqft)
CENT_TO_SQFT = 435.6           # Standard South India (1 Cent = 1/100 Acre = 435.6 sqft)
ANKANAM_TO_SQFT = 72.0         # Standard Andhra Pradesh / Rayalaseema (1 Ankanam = 72 sqft)
GUNTA_TO_SQFT = 1089.0         # Default Gunta (1 Gunta = 121 sq yards = 1089 sqft)
BISWA_DEFAULT_TO_SQFT = 1350.0 # Default Biswa (UP standard ~1350 sqft)
BIGHABIGHAI_DEFAULT = 27000.0  # Default standard Bigha (UP/Bihar standard ~27,000 sqft = 20 Biswa)
MARLA_DEFAULT_TO_SQFT = 272.25 # Standard Marla (Punjab/Haryana ~272.25 sqft = 9 Sarsahi)
KANAL_DEFAULT_TO_SQFT = 5445.0 # Standard Kanal (Punjab/Haryana = 20 Marlas = 5445 sqft)
CHATAK_DEFAULT_TO_SQFT = 45.0  # West Bengal Chatak (1/16 Cottah = 45 sqft)
COTTAH_DEFAULT_TO_SQFT = 720.0 # West Bengal Cottah (Katha = 720 sqft)

# State-specific / Regional unit conversion multipliers (in sqft)
# Because land measurement in India is governed by State Revenue Codes:
REGIONAL_CONVERSIONS: Dict[str, Dict[str, float]] = {
    "Karnataka": {
        "GUNTA": 1089.0,         # 1 Gunta = 121 sq yds = 1089 sqft (40 Guntas = 1 Acre)
        "ACRE": 43560.0,
        "CENT": 435.6,
        "ANKANAM": 72.0,
    },
    "Maharashtra": {
        "GUNTA": 1089.0,         # 1 Gunta = 121 sq yds = 1089 sqft
        "ACRE": 43560.0,
        "HECTARE": 107639.104,
        "VAAR": 9.0,             # 1 Vaar = 1 Gaj / Sq Yd = 9 sqft
    },
    "Tamil Nadu": {
        "GROUND": 2400.0,        # 1 Ground = 2400 sqft (~222.96 sqm)
        "CENT": 435.6,           # 1 Cent = 435.6 sqft (100 Cents = 1 Acre)
        "ACRE": 43560.0,
        "KUZHI": 144.0,          # 1 Kuzhi = 144 sqft
        "MAA": 4356.0,           # 1 Maa = 100 Kuzhis = 4356 sqft (10 Maa = 1 Veli)
        "VELI": 43560.0,         # 1 Veli = 2000 Kuzhis = 43560 sqft (~1 Acre)
    },
    "Telangana": {
        "GUNTA": 1089.0,         # 1 Gunta = 1089 sqft
        "ANKANAM": 72.0,         # 1 Ankanam = 72 sqft
        "SQYD": 9.0,             # Gaj / Square Yards standard in HMDA
        "ACRE": 43560.0,
    },
    "Andhra Pradesh": {
        "ANKANAM": 72.0,         # Standard Rayalaseema & Coastal AP = 72 sqft (8 sq yards)
        "CENT": 435.6,           # 1 Cent = 435.6 sqft
        "GUNTA": 1089.0,
        "ACRE": 43560.0,
    },
    "Kerala": {
        "CENT": 435.6,           # 1 Cent = 435.6 sqft
        "ACRE": 43560.0,
        "PERCH": 272.25,         # 1 Perch = 272.25 sqft
    },
    "Uttar Pradesh": {
        "BISWA": 1350.0,         # Standard UP Biswa = 1350 sqft (Pukka)
        "BIGHA": 27000.0,        # UP Pukka Bigha = 20 Biswa = 27,000 sqft (~3,000 sq yds)
        "SQYD": 9.0,             # Gaj
        "ACRE": 43560.0,
    },
    "Haryana": {
        "MARLA": 272.25,         # 1 Marla = 9 Sarsahi = 272.25 sqft
        "KANAL": 5445.0,         # 1 Kanal = 20 Marlas = 5445 sqft
        "BIGHA": 9075.0,         # Haryana/Punjab Kachha Bigha = 9075 sqft (approx)
        "BISWA": 453.75,         # Haryana Biswa = 453.75 sqft
        "SQYD": 9.0,             # Gaj
        "ACRE": 43560.0,         # 1 Killa / Acre = 8 Kanals = 43560 sqft
    },
    "Punjab": {
        "MARLA": 272.25,
        "KANAL": 5445.0,
        "ACRE": 43560.0,         # 1 Killa = 43560 sqft
        "SQYD": 9.0,
    },
    "Delhi": {
        "SQYD": 9.0,             # Gaj
        "BISWA": 1350.0,
        "BIGHA": 27000.0,
        "ACRE": 43560.0,
    },
    "West Bengal": {
        "CHATAK": 45.0,          # 1 Chatak = 45 sqft
        "COTTAH": 720.0,         # 1 Cottah (Katha) = 16 Chataks = 720 sqft
        "BIGHA": 14400.0,        # 1 Bigha = 20 Cottahs = 14400 sqft (~1600 sq yds)
        "ACRE": 43560.0,
    },
    "Gujarat": {
        "VAAR": 9.0,             # 1 Vaar = 1 Gaj / Sq Yd = 9 sqft
        "VIGH": 24000.0,         # Gujarat Vigha = 24,000 sqft
        "GUNTA": 1089.0,
        "ACRE": 43560.0,
    },
}

UNIT_ALIASES = {
    # Square Feet
    "sqft": AreaUnit.SQFT,
    "sq ft": AreaUnit.SQFT,
    "sq_ft": AreaUnit.SQFT,
    "sq.ft": AreaUnit.SQFT,
    "square feet": AreaUnit.SQFT,
    "square foot": AreaUnit.SQFT,
    "sft": AreaUnit.SQFT,
    "feet": AreaUnit.SQFT,

    # Square Metres
    "sqm": AreaUnit.SQM,
    "sq m": AreaUnit.SQM,
    "sq_m": AreaUnit.SQM,
    "sq.m": AreaUnit.SQM,
    "square metre": AreaUnit.SQM,
    "square meters": AreaUnit.SQM,
    "square meter": AreaUnit.SQM,

    # Square Yards / Gaj / Vaar
    "sqyd": AreaUnit.SQYD,
    "sq yd": AreaUnit.SQYD,
    "sq_yd": AreaUnit.SQYD,
    "sq.yd": AreaUnit.SQYD,
    "square yard": AreaUnit.SQYD,
    "square yards": AreaUnit.SQYD,
    "gaj": AreaUnit.SQYD,
    "vaar": AreaUnit.VAAR,
    "yard": AreaUnit.SQYD,

    # Acre
    "acre": AreaUnit.ACRE,
    "acres": AreaUnit.ACRE,
    "killa": AreaUnit.ACRE,

    # Hectare
    "hectare": AreaUnit.HECTARE,
    "hectares": AreaUnit.HECTARE,
    "ha": AreaUnit.HECTARE,

    # Regional Units
    "gunta": AreaUnit.GUNTA,
    "guntas": AreaUnit.GUNTA,
    "guntha": AreaUnit.GUNTA,
    "gunthas": AreaUnit.GUNTA,
    "ground": AreaUnit.GROUND,
    "grounds": AreaUnit.GROUND,
    "cent": AreaUnit.CENT,
    "cents": AreaUnit.CENT,
    "ankanam": AreaUnit.ANKANAM,
    "ankanams": AreaUnit.ANKANAM,
    "bigha": AreaUnit.BIGHA,
    "bighas": AreaUnit.BIGHA,
    "vigha": AreaUnit.BIGHA,
    "biswa": AreaUnit.BISWA,
    "biswas": AreaUnit.BISWA,
    "marla": AreaUnit.MARLA,
    "marlas": AreaUnit.MARLA,
    "kanal": AreaUnit.KANAL,
    "kanals": AreaUnit.KANAL,
    "cottah": AreaUnit.COTTAH,
    "katha": AreaUnit.COTTAH,
    "chatak": AreaUnit.CHATAK,
    "kuzhi": AreaUnit.KUZHI,
    "maa": AreaUnit.MAA,
}


def parse_and_normalize_area(
    raw_value: Any,
    raw_unit: Optional[str] = None,
    state: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
    """Parse raw area representation and convert to standard square feet using regional rules.

    Preserves original numeric value and unit while delivering normalized square footage.

    Returns:
        (normalized_sqft, original_numeric_value, original_unit_string, error_message)
    """
    if raw_value is None:
        return None, None, None, "Area value is missing"

    unit_candidate = (raw_unit or "").strip().lower()
    num_val: Optional[float] = None

    if isinstance(raw_value, (int, float)):
        num_val = float(raw_value)
    else:
        s = str(raw_value).strip().lower()
        if not s or s in ("nan", "null", "none", "na"):
            return None, None, None, "Empty or null area value"

        # Check if text contains embedded unit keyword
        for alias, matched_unit in UNIT_ALIASES.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", s):
                unit_candidate = alias
                break

        # Extract numeric characters
        clean_num = re.sub(r"[^\d\.]", "", s)
        try:
            num_val = float(clean_num)
        except ValueError:
            return None, None, None, f"Cannot parse numeric area from '{raw_value}'"

    if num_val is None or num_val <= 0:
        return None, None, None, f"Area must be strictly positive (got {num_val})"

    # Resolve unit to standard AreaUnit enum
    resolved_unit = UNIT_ALIASES.get(unit_candidate, AreaUnit.SQFT)
    original_unit_label = resolved_unit.value

    # Determine regional state conversions if state is provided
    state_table = REGIONAL_CONVERSIONS.get(state or "", {})

    # Apply deterministic and regionally calibrated conversions
    if resolved_unit == AreaUnit.SQFT:
        norm_sqft = num_val
    elif resolved_unit == AreaUnit.SQM:
        norm_sqft = num_val * SQM_TO_SQFT
    elif resolved_unit == AreaUnit.SQYD or resolved_unit == AreaUnit.VAAR:
        norm_sqft = num_val * SQYD_TO_SQFT
    elif resolved_unit == AreaUnit.ACRE:
        norm_sqft = num_val * ACRE_TO_SQFT
    elif resolved_unit == AreaUnit.HECTARE:
        norm_sqft = num_val * HECTARE_TO_SQFT
    elif resolved_unit == AreaUnit.GUNTA:
        factor = state_table.get("GUNTA", GUNTA_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.GROUND:
        factor = state_table.get("GROUND", GROUND_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.CENT:
        factor = state_table.get("CENT", CENT_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.ANKANAM:
        factor = state_table.get("ANKANAM", ANKANAM_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.BIGHA:
        factor = state_table.get("BIGHA", BIGHABIGHAI_DEFAULT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.BISWA:
        factor = state_table.get("BISWA", BISWA_DEFAULT_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.MARLA:
        factor = state_table.get("MARLA", MARLA_DEFAULT_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.KANAL:
        factor = state_table.get("KANAL", KANAL_DEFAULT_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.COTTAH:
        factor = state_table.get("COTTAH", COTTAH_DEFAULT_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.CHATAK:
        factor = state_table.get("CHATAK", CHATAK_DEFAULT_TO_SQFT)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.KUZHI:
        factor = state_table.get("KUZHI", 144.0)
        norm_sqft = num_val * factor
    elif resolved_unit == AreaUnit.MAA:
        factor = state_table.get("MAA", 4356.0)
        norm_sqft = num_val * factor
    else:
        norm_sqft = num_val

    return round(norm_sqft, 2), num_val, original_unit_label, None
