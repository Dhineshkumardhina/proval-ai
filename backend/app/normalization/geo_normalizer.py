"""Geographic name standardization, postal code validation, and spatial bounds validation for India."""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

# Bounding box for the Republic of India: Lat 6.0° to 37.6° N, Lon 68.1° to 97.4° E
# Mainland southernmost point: Cape Comorin ~8.07° N, southernmost island: Indira Point ~6.75° N.
# Northernmost mainland border: ~37.1° N.
# Westernmost mainland: Ghuar Mota (Gujarat) ~68.12° E.
# Easternmost mainland: Kibithu (Arunachal Pradesh) ~97.42° E.
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 37.6
INDIA_LON_MIN, INDIA_LON_MAX = 68.1, 97.4

# Authoritative State / Union Territory Bounding Boxes [lat_min, lat_max, lon_min, lon_max]
STATE_BOUNDING_BOXES: Dict[str, Tuple[float, float, float, float]] = {
    "Karnataka": (11.5, 18.5, 74.0, 78.6),
    "Maharashtra": (15.6, 22.1, 72.6, 80.9),
    "Tamil Nadu": (8.0, 13.6, 76.2, 80.4),
    "Telangana": (15.8, 19.9, 77.2, 81.8),
    "Andhra Pradesh": (12.6, 19.2, 76.7, 84.8),
    "Delhi": (28.4, 28.9, 76.8, 77.4),
    "Haryana": (27.6, 30.9, 74.4, 77.6),
    "Uttar Pradesh": (23.8, 30.5, 77.0, 84.7),
    "Kerala": (8.2, 12.8, 74.8, 77.6),
    "West Bengal": (21.5, 27.3, 85.8, 89.9),
    "Gujarat": (20.1, 24.7, 68.1, 74.5),
    "Rajasthan": (23.0, 30.2, 69.5, 78.3),
    "Madhya Pradesh": (21.1, 26.9, 74.0, 82.8),
    "Punjab": (29.5, 32.5, 73.8, 76.9),
    "Odisha": (17.8, 22.6, 81.3, 87.5),
    "Bihar": (24.3, 27.6, 83.3, 88.3),
    "Goa": (14.9, 15.8, 73.6, 74.4),
    "Assam": (24.1, 28.2, 89.7, 96.0),
}

# Standardized Indian States and Union Territories mapping (all 28 states + 8 UTs + common aliases)
STATE_CANONICAL_MAP: Dict[str, str] = {
    # Southern States
    "karnataka": "Karnataka",
    "ka": "Karnataka",
    "blr": "Karnataka",
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "tamil nadu": "Tamil Nadu",
    "tn": "Tamil Nadu",
    "chennai": "Tamil Nadu",
    "madras": "Tamil Nadu",
    "telangana": "Telangana",
    "ts": "Telangana",
    "tg": "Telangana",
    "hyderabad": "Telangana",
    "andhra pradesh": "Andhra Pradesh",
    "ap": "Andhra Pradesh",
    "andhra": "Andhra Pradesh",
    "kerala": "Kerala",
    "kl": "Kerala",

    # Western States
    "maharashtra": "Maharashtra",
    "mh": "Maharashtra",
    "mumbai": "Maharashtra",
    "pune": "Maharashtra",
    "bombay": "Maharashtra",
    "gujarat": "Gujarat",
    "gj": "Gujarat",
    "goa": "Goa",
    "ga": "Goa",

    # Northern & Central States
    "delhi": "Delhi",
    "nct of delhi": "Delhi",
    "dl": "Delhi",
    "new delhi": "Delhi",
    "national capital territory of delhi": "Delhi",
    "haryana": "Haryana",
    "hr": "Haryana",
    "gurgaon": "Haryana",
    "gurugram": "Haryana",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "noida": "Uttar Pradesh",
    "rajasthan": "Rajasthan",
    "rj": "Rajasthan",
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "punjab": "Punjab",
    "pb": "Punjab",
    "chandigarh": "Chandigarh",
    "ch": "Chandigarh",
    "himachal pradesh": "Himachal Pradesh",
    "hp": "Himachal Pradesh",
    "uttarakhand": "Uttarakhand",
    "uk": "Uttarakhand",
    "uttaranchal": "Uttarakhand",
    "jammu and kashmir": "Jammu and Kashmir",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "ladakh": "Ladakh",

    # Eastern & North-Eastern States
    "west bengal": "West Bengal",
    "wb": "West Bengal",
    "kolkata": "West Bengal",
    "calcutta": "West Bengal",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "or": "Odisha",
    "od": "Odisha",
    "bihar": "Bihar",
    "br": "Bihar",
    "jharkhand": "Jharkhand",
    "jh": "Jharkhand",
    "chhattisgarh": "Chhattisgarh",
    "cg": "Chhattisgarh",
    "assam": "Assam",
    "as": "Assam",
    "sikkim": "Sikkim",
    "sk": "Sikkim",
    "meghalaya": "Meghalaya",
    "ml": "Meghalaya",
    "tripura": "Tripura",
    "tr": "Tripura",
    "mizoram": "Mizoram",
    "mz": "Mizoram",
    "manipur": "Manipur",
    "mn": "Manipur",
    "nagaland": "Nagaland",
    "nl": "Nagaland",
    "arunachal pradesh": "Arunachal Pradesh",
    "ar": "Arunachal Pradesh",

    # Union Territories
    "puducherry": "Puducherry",
    "py": "Puducherry",
    "pondicherry": "Puducherry",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "an": "Andaman and Nicobar Islands",
    "lakshadweep": "Lakshadweep",
    "ld": "Lakshadweep",
}

# Major district name canonicalizations
DISTRICT_CANONICAL_MAP: Dict[str, str] = {
    # Karnataka
    "bangalore": "Bengaluru Urban",
    "bangalore urban": "Bengaluru Urban",
    "bengaluru": "Bengaluru Urban",
    "bengaluru urban": "Bengaluru Urban",
    "bangalore rural": "Bengaluru Rural",
    "bengaluru rural": "Bengaluru Rural",
    "mysore": "Mysuru",
    "mysuru": "Mysuru",
    "mangalore": "Dakshina Kannada",
    "dakshina kannada": "Dakshina Kannada",
    "belgaum": "Belagavi",
    "belagavi": "Belagavi",
    "tumkur": "Tumakuru",
    "tumakuru": "Tumakuru",

    # Maharashtra
    "mumbai": "Mumbai City",
    "mumbai city": "Mumbai City",
    "mumbai suburban": "Mumbai Suburban",
    "bombay": "Mumbai City",
    "pune": "Pune",
    "poona": "Pune",
    "thane": "Thane",
    "navi mumbai": "Thane",
    "nagpur": "Nagpur",
    "nashik": "Nashik",
    "nasik": "Nashik",
    "aurangabad": "Chhatrapati Sambhajinagar",
    "chhatrapati sambhajinagar": "Chhatrapati Sambhajinagar",

    # Tamil Nadu
    "chennai": "Chennai",
    "madras": "Chennai",
    "kanchipuram": "Kanchipuram",
    "kancheepuram": "Kanchipuram",
    "chengalpattu": "Chengalpattu",
    "thiruvallur": "Tiruvallur",
    "tiruvallur": "Tiruvallur",
    "coimbatore": "Coimbatore",
    "kovai": "Coimbatore",
    "madurai": "Madurai",

    # Telangana & Andhra Pradesh
    "hyderabad": "Hyderabad",
    "rangareddy": "Ranga Reddy",
    "ranga reddy": "Ranga Reddy",
    "medchal": "Medchal-Malkajgiri",
    "medchal malkajgiri": "Medchal-Malkajgiri",
    "medchal-malkajgiri": "Medchal-Malkajgiri",
    "sangareddy": "Sangareddy",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "vijayawada": "NTR",
    "guntur": "Guntur",

    # NCR / North
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "faridabad": "Faridabad",
    "gautam buddha nagar": "Gautam Buddha Nagar",
    "noida": "Gautam Buddha Nagar",
    "greater noida": "Gautam Buddha Nagar",
    "ghaziabad": "Ghaziabad",
    "central delhi": "Central Delhi",
    "east delhi": "East Delhi",
    "new delhi": "New Delhi",
    "north delhi": "North Delhi",
    "north east delhi": "North East Delhi",
    "north west delhi": "North West Delhi",
    "south delhi": "South Delhi",
    "south east delhi": "South East Delhi",
    "south west delhi": "South West Delhi",
    "west delhi": "West Delhi",

    # West Bengal
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "north 24 parganas": "North 24 Parganas",
    "south 24 parganas": "South 24 Parganas",
    "howrah": "Howrah",

    # Gujarat
    "ahmedabad": "Ahmedabad",
    "surat": "Surat",
    "vadodara": "Vadodara",
    "baroda": "Vadodara",
}

# Subdistrict / Taluk / Tehsil canonicalizations
SUBDISTRICT_CANONICAL_MAP: Dict[str, str] = {
    # Bengaluru Urban Taluks
    "bangalore south": "Bengaluru South",
    "bengaluru south": "Bengaluru South",
    "bangalore north": "Bengaluru North",
    "bengaluru north": "Bengaluru North",
    "bangalore east": "Bengaluru East",
    "bengaluru east": "Bengaluru East",
    "krishnarajapuram": "KR Puram",
    "kr puram": "KR Puram",
    "anekal": "Anekal",
    "yelahanka": "Yelahanka",

    # Mumbai / Pune Taluks
    "andheri": "Andheri",
    "borivali": "Borivali",
    "kurla": "Kurla",
    "haveli": "Haveli",
    "mulshi": "Mulshi",
    "maval": "Maval",

    # Chennai / Chengalpattu / Kanchipuram Taluks
    "guindy": "Guindy",
    "velachery": "Velachery",
    "egmore": "Egmore",
    "sholinganallur": "Sholinganallur",
    "tambaram": "Tambaram",
    "vandalur": "Vandalur",

    # Hyderabad / Ranga Reddy Mandals
    "serilingampally": "Serilingampally",
    "rajendranagar": "Rajendranagar",
    "balanagar": "Balanagar",
    "uppal": "Uppal",
    "ghatkesar": "Ghatkesar",
}

# Major City canonicalization
CITY_CANONICAL_MAP: Dict[str, str] = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "blr": "Bengaluru",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "pune": "Pune",
    "poona": "Pune",
    "madras": "Chennai",
    "chennai": "Chennai",
    "hyderabad": "Hyderabad",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "noida": "Noida",
    "greater noida": "Greater Noida",
    "ghaziabad": "Ghaziabad",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "ahmedabad": "Ahmedabad",
    "surat": "Surat",
}

# PIN-code prefix to State / Postal Circle mapping (First 2 digits)
PINCODE_ZONE_MAP: Dict[str, str] = {
    "11": "Delhi",
    "12": "Haryana",
    "13": "Haryana",
    "14": "Punjab",
    "15": "Punjab",
    "16": "Chandigarh",
    "17": "Himachal Pradesh",
    "18": "Jammu and Kashmir",
    "19": "Jammu and Kashmir",
    "20": "Uttar Pradesh",
    "21": "Uttar Pradesh",
    "22": "Uttar Pradesh",
    "23": "Uttar Pradesh",
    "24": "Uttar Pradesh",
    "25": "Uttar Pradesh",
    "26": "Uttarakhand",
    "27": "Uttar Pradesh",
    "28": "Uttar Pradesh",
    "30": "Rajasthan",
    "31": "Rajasthan",
    "32": "Rajasthan",
    "33": "Rajasthan",
    "34": "Rajasthan",
    "36": "Gujarat",
    "37": "Gujarat",
    "38": "Gujarat",
    "39": "Gujarat",
    "40": "Maharashtra",
    "41": "Maharashtra",
    "42": "Maharashtra",
    "43": "Maharashtra",
    "44": "Maharashtra",
    "45": "Madhya Pradesh",
    "46": "Madhya Pradesh",
    "47": "Madhya Pradesh",
    "48": "Madhya Pradesh",
    "49": "Chhattisgarh",
    "50": "Telangana",
    "51": "Andhra Pradesh",
    "52": "Andhra Pradesh",
    "53": "Andhra Pradesh",
    "56": "Karnataka",
    "57": "Karnataka",
    "58": "Karnataka",
    "59": "Karnataka",
    "60": "Tamil Nadu",
    "61": "Tamil Nadu",
    "62": "Tamil Nadu",
    "63": "Tamil Nadu",
    "64": "Tamil Nadu",
    "67": "Kerala",
    "68": "Kerala",
    "69": "Kerala",
    "70": "West Bengal",
    "71": "West Bengal",
    "72": "West Bengal",
    "73": "West Bengal",
    "74": "West Bengal",
    "75": "Odisha",
    "76": "Odisha",
    "77": "Odisha",
    "78": "Assam",
    "79": "North East",
    "80": "Bihar",
    "81": "Bihar",
    "82": "Jharkhand",
    "83": "Jharkhand",
    "84": "Bihar",
    "85": "Bihar",
}


def normalize_state(raw_state: Optional[str]) -> Tuple[str, Optional[str]]:
    """Standardize state names into official title-case state/UT name."""
    if not raw_state:
        return "Unknown", "Missing state value"
    s = raw_state.strip().lower()
    canonical = STATE_CANONICAL_MAP.get(s)
    if canonical:
        return canonical, None
    return raw_state.strip().title(), None


def normalize_district(raw_district: Optional[str]) -> Tuple[str, Optional[str]]:
    """Standardize district names into official district nomenclature."""
    if not raw_district:
        return "Unknown", "Missing district value"
    s = raw_district.strip().lower()
    canonical = DISTRICT_CANONICAL_MAP.get(s)
    if canonical:
        return canonical, None
    return raw_district.strip().title(), None


def normalize_subdistrict(raw_subdistrict: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Standardize subdistrict (taluk/tehsil/mandal) names."""
    if not raw_subdistrict:
        return None, "Subdistrict not provided"
    s = raw_subdistrict.strip().lower()
    canonical = SUBDISTRICT_CANONICAL_MAP.get(s)
    if canonical:
        return canonical, None
    return raw_subdistrict.strip().title(), None


def normalize_city(raw_city: Optional[str]) -> Tuple[str, Optional[str]]:
    """Standardize municipal / metro city names."""
    if not raw_city:
        return "Unknown", "Missing city value"
    s = raw_city.strip().lower()
    canonical = CITY_CANONICAL_MAP.get(s)
    if canonical:
        return canonical, None
    return raw_city.strip().title(), None


def normalize_pincode(
    raw_pincode: Any,
    expected_state: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Validate Indian 6-digit postal PIN code (e.g. 560066) and optionally cross-check state circle."""
    if not raw_pincode:
        return None, "PIN code not provided"
    clean = re.sub(r"[^\d]", "", str(raw_pincode).strip())
    if len(clean) != 6 or clean[0] == "0":
        return None, f"Invalid Indian PIN code format: '{raw_pincode}' (must be 6 digits and not start with 0)"

    # Check state correspondence if state is specified
    if expected_state:
        prefix = clean[:2]
        expected_circle = PINCODE_ZONE_MAP.get(prefix)
        if expected_circle and expected_state != "Unknown":
            # Normalize expected state for comparison
            canonical_expected, _ = normalize_state(expected_state)
            if expected_circle != canonical_expected and expected_circle != "North East":
                return clean, (
                    f"PIN prefix '{prefix}xx' maps to postal circle '{expected_circle}', "
                    f"which mismatches declared state '{canonical_expected}'"
                )

    return clean, None


class CoordinateValidationResult:
    """Detailed result object containing normalized coordinates, status, and precision metrics."""
    def __init__(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        error_message: Optional[str] = None,
        original_latitude: Optional[float] = None,
        original_longitude: Optional[float] = None,
        precision_digits: Optional[int] = None,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.error_message = error_message
        self.original_latitude = original_latitude
        self.original_longitude = original_longitude
        self.precision_digits = precision_digits

    # Allow tuple unpacking for backward compatibility: lat, lon, err = validate_and_normalize_coordinates(...)
    def __iter__(self):
        yield self.latitude
        yield self.longitude
        yield self.error_message

    def __getitem__(self, index):
        return [self.latitude, self.longitude, self.error_message][index]

    def __len__(self):
        return 3


def validate_and_normalize_coordinates(
    lat: Any,
    lon: Any,
    state: Optional[str] = None,
) -> CoordinateValidationResult:
    """Validate geographic coordinates strictly against Indian territorial bounds and optional state bounding boxes.

    Preserves original coordinates and calculates coordinate precision (decimal places).
    Supports 3-tuple unpacking (latitude, longitude, error_message) for backward compatibility,
    as well as accessing attributes .original_latitude, .original_longitude, .precision_digits.
    """
    if lat is None or lon is None:
        return CoordinateValidationResult(None, None, None, None, None, None)  # Lawfully missing, never fabricated

    # Capture original values
    orig_lat_str = str(lat).strip()
    orig_lon_str = str(lon).strip()

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (ValueError, TypeError):
        return CoordinateValidationResult(
            None, None, f"Coordinates could not be parsed to float: lat='{lat}', lon='{lon}'", None, None, None
        )

    # Calculate decimal precision from original representation
    def get_precision(s: str) -> int:
        if "." in s:
            return len(s.split(".")[1].rstrip("0"))
        return 0

    precision_digits = max(get_precision(orig_lat_str), get_precision(orig_lon_str))

    # Check for (0,0) null island
    if abs(lat_f) < 0.0001 and abs(lon_f) < 0.0001:
        return CoordinateValidationResult(
            None, None, "Invalid (0,0) null-island coordinates", lat_f, lon_f, precision_digits
        )

    # Inverted lat/long check (common error where longitude is passed as latitude)
    # Latitude in India is ~6-37°N; Longitude is ~68-97°E.
    if INDIA_LON_MIN <= lat_f <= INDIA_LON_MAX and INDIA_LAT_MIN <= lon_f <= INDIA_LAT_MAX:
        # Swap back to correct orientation
        lat_f, lon_f = lon_f, lat_f

    # National Indian Territorial Bounds validation
    if not (INDIA_LAT_MIN <= lat_f <= INDIA_LAT_MAX and INDIA_LON_MIN <= lon_f <= INDIA_LON_MAX):
        return CoordinateValidationResult(
            None,
            None,
            (
                f"Coordinates ({lat_f:.6f}, {lon_f:.6f}) fall outside Indian geographic boundaries "
                f"[{INDIA_LAT_MIN}° to {INDIA_LAT_MAX}° N, {INDIA_LON_MIN}° to {INDIA_LON_MAX}° E]"
            ),
            lat_f,
            lon_f,
            precision_digits,
        )

    # State-level authoritative bounding box check (if state provided and recognized)
    if state:
        canonical_state, _ = normalize_state(state)
        bbox = STATE_BOUNDING_BOXES.get(canonical_state)
        if bbox:
            s_lat_min, s_lat_max, s_lon_min, s_lon_max = bbox
            if not (s_lat_min <= lat_f <= s_lat_max and s_lon_min <= lon_f <= s_lon_max):
                return CoordinateValidationResult(
                    None,
                    None,
                    (
                        f"Coordinates ({lat_f:.6f}, {lon_f:.6f}) fall outside authoritative boundary for "
                        f"{canonical_state} [{s_lat_min}-{s_lat_max}°N, {s_lon_min}-{s_lon_max}°E]"
                    ),
                    lat_f,
                    lon_f,
                    precision_digits,
                )

    # Return normalized rounded to 6 decimal places (~0.1m precision) along with preserved originals
    return CoordinateValidationResult(
        round(lat_f, 6), round(lon_f, 6), None, lat_f, lon_f, precision_digits
    )


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 3)


class CadastralReference:
    """Standardized representation of Indian revenue cadastral property identifiers."""

    def __init__(
        self,
        survey_number: Optional[str] = None,
        khasra_number: Optional[str] = None,
        cts_number: Optional[str] = None,
        gat_number: Optional[str] = None,
        plot_number: Optional[str] = None,
        village_name: Optional[str] = None,
        taluka_tehsil: Optional[str] = None,
        district: Optional[str] = None,
        sro_jurisdiction_code: Optional[str] = None,
        cadastral_parcel_id: Optional[str] = None,
        spatial_accuracy_tier: str = "COORDINATE_BOUNDED",
        validation_status: str = "UNVERIFIED",
        validation_notes: Optional[str] = None,
    ):
        self.survey_number = survey_number
        self.khasra_number = khasra_number
        self.cts_number = cts_number
        self.gat_number = gat_number
        self.plot_number = plot_number
        self.village_name = village_name
        self.taluka_tehsil = taluka_tehsil
        self.district = district
        self.sro_jurisdiction_code = sro_jurisdiction_code
        self.cadastral_parcel_id = cadastral_parcel_id
        self.spatial_accuracy_tier = spatial_accuracy_tier
        self.validation_status = validation_status
        self.validation_notes = validation_notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "survey_number": self.survey_number,
            "khasra_number": self.khasra_number,
            "cts_number": self.cts_number,
            "gat_number": self.gat_number,
            "plot_number": self.plot_number,
            "village_name": self.village_name,
            "taluka_tehsil": self.taluka_tehsil,
            "district": self.district,
            "sro_jurisdiction_code": self.sro_jurisdiction_code,
            "cadastral_parcel_id": self.cadastral_parcel_id,
            "spatial_accuracy_tier": self.spatial_accuracy_tier,
            "validation_status": self.validation_status,
            "validation_notes": self.validation_notes,
        }


def normalize_cadastral_reference(
    raw_data: Dict[str, Any],
    state: Optional[str] = None,
    city: Optional[str] = None,
) -> CadastralReference:
    """Extract, parse, and normalize Indian cadastral parcel identifiers from deed payloads.
    
    Supports:
    - Survey Number / Hissa (South India / Karnataka / Tamil Nadu / Telangana)
    - Khasra / Killa / Murabba (North India / Haryana / UP / Punjab / Rajasthan)
    - CTS Number (City Title Survey) / CS (Urban Maharashtra / Mumbai / Pune)
    - Gat Number / Gut (Rural Maharashtra)
    - Plot / Dag Number (West Bengal / Eastern India)
    """
    survey = (
        raw_data.get("survey_number")
        or raw_data.get("survey_no")
        or raw_data.get("sy_no")
        or raw_data.get("surveyNumber")
    )
    khasra = (
        raw_data.get("khasra_number")
        or raw_data.get("khasra_no")
        or raw_data.get("khasra")
        or raw_data.get("khasraNumber")
    )
    cts = (
        raw_data.get("cts_number")
        or raw_data.get("cts_no")
        or raw_data.get("cts")
        or raw_data.get("ctsNumber")
    )
    gat = (
        raw_data.get("gat_number")
        or raw_data.get("gat_no")
        or raw_data.get("gatNumber")
    )
    plot = (
        raw_data.get("plot_number")
        or raw_data.get("plot_no")
        or raw_data.get("plotNumber")
    )
    village = (
        raw_data.get("village_name")
        or raw_data.get("village")
        or raw_data.get("revenue_village")
    )
    taluka = (
        raw_data.get("taluka_tehsil")
        or raw_data.get("taluka")
        or raw_data.get("tehsil")
        or raw_data.get("sub_district")
    )
    sro_code = (
        raw_data.get("sro_jurisdiction_code")
        or raw_data.get("sro_code")
        or raw_data.get("sro")
        or raw_data.get("sub_registrar_office")
    )

    clean_survey = str(survey).strip() if survey is not None else None
    clean_khasra = str(khasra).strip() if khasra is not None else None
    clean_cts = str(cts).strip() if cts is not None else None
    clean_gat = str(gat).strip() if gat is not None else None
    clean_plot = str(plot).strip() if plot is not None else None
    clean_village = str(village).strip() if village is not None else None
    clean_taluka = str(taluka).strip() if taluka is not None else None
    clean_sro = str(sro_code).strip() if sro_code is not None else None

    # Primary identifier selection based on regional context
    primary_id = clean_survey or clean_cts or clean_khasra or clean_gat or clean_plot

    if not primary_id:
        return CadastralReference(
            village_name=clean_village,
            taluka_tehsil=clean_taluka,
            sro_jurisdiction_code=clean_sro,
            spatial_accuracy_tier="COORDINATE_BOUNDED",
            validation_status="MISSING",
            validation_notes="No survey number, CTS number, or Khasra parcel identifier found in transaction payload.",
        )

    # Sanitize and validate identifier format (Alphanumeric with slash/hyphen/dot allowed)
    valid_format = bool(re.match(r"^[A-Za-z0-9\-\.\/\_]+$", primary_id))
    if not valid_format:
        return CadastralReference(
            survey_number=clean_survey,
            khasra_number=clean_khasra,
            cts_number=clean_cts,
            gat_number=clean_gat,
            plot_number=clean_plot,
            village_name=clean_village,
            taluka_tehsil=clean_taluka,
            sro_jurisdiction_code=clean_sro,
            spatial_accuracy_tier="COORDINATE_BOUNDED",
            validation_status="SYNTAX_ERROR",
            validation_notes=f"Cadastral identifier '{primary_id}' contains invalid characters.",
        )

    # Construct canonical synthetic parcel identifier
    state_prefix = (state[:2].upper() if state else "IN")
    dist_prefix = (city[:3].upper() if city else "URB")
    vill_prefix = (clean_village[:3].upper() if clean_village else "GEN")
    canonical_parcel_id = f"{state_prefix}-{dist_prefix}-{vill_prefix}-{primary_id}".replace(" ", "_")

    return CadastralReference(
        survey_number=clean_survey or primary_id,
        khasra_number=clean_khasra,
        cts_number=clean_cts,
        gat_number=clean_gat,
        plot_number=clean_plot,
        village_name=clean_village,
        taluka_tehsil=clean_taluka,
        sro_jurisdiction_code=clean_sro,
        cadastral_parcel_id=canonical_parcel_id,
        spatial_accuracy_tier="PARCEL_SURVEY_RECORDED",
        validation_status="VALIDATED",
        validation_notes="Cadastral identifier parsed and structured. Government digital revenue map (BhuNaksha) shapefile boundary verification requires state department MoU.",
    )


# Reference centers for key urban jurisdictions (lat, lon, max_radius_km)
URBAN_CENTROID_BOUNDS: Dict[str, Tuple[float, float, float]] = {
    "Bengaluru": (12.9716, 77.5946, 60.0),
    "Bangalore": (12.9716, 77.5946, 60.0),
    "Mumbai": (19.0760, 72.8777, 50.0),
    "Pune": (18.5204, 73.8567, 45.0),
    "Chennai": (13.0827, 80.2707, 45.0),
    "Hyderabad": (17.3850, 78.4867, 50.0),
    "Delhi": (28.7041, 77.1025, 45.0),
    "Noida": (28.5355, 77.3910, 30.0),
    "Gurugram": (28.4595, 77.0266, 35.0),
    "Gurgaon": (28.4595, 77.0266, 35.0),
    "Kolkata": (22.5726, 88.3639, 45.0),
    "Ahmedabad": (23.0225, 72.5714, 40.0),
}


def validate_locality_spatial_consistency(
    latitude: Optional[float],
    longitude: Optional[float],
    city: Optional[str],
    locality: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Verify geographic consistency between coordinates and declared urban jurisdiction.
    
    Protects against coordinates falling in the sea or hundreds of kilometers away from the declared city.
    """
    if latitude is None or longitude is None or not city:
        return True, None  # Lawfully missing

    ref = URBAN_CENTROID_BOUNDS.get(city.strip())
    if not ref:
        return True, None  # City centroid not configured in baseline catalog

    c_lat, c_lon, max_km = ref
    dist_km = haversine_distance_km(latitude, longitude, c_lat, c_lon)

    if dist_km > max_km:
        return False, (
            f"Spatial inconsistency detected: Coordinates ({latitude:.4f}, {longitude:.4f}) are {dist_km:.1f} km "
            f"from the center of {city} (threshold: {max_km:.1f} km). Outlier coordinates may fall in coastal waters or outside municipal jurisdiction."
        )

    return True, None

