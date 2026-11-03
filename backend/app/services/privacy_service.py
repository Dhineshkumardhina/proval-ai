"""Privacy, Security, and PII Redaction Engine (Phase 2G).

Compliant with India's Digital Personal Data Protection Act, 2023 (DPDP Act 2023)
data minimization and purpose limitation principles.
"""

import re
from typing import Dict, List, Tuple, Any


# Regex patterns for Indian PII identifiers
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
# Aadhaar: 12 digits, UIDAI standard does not start with 0 or 1, optional spaces or hyphens
AADHAAR_REGEX = re.compile(r"\b[2-9][0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b")
# Indian mobile phone numbers: optional +91 prefix, 10 digits starting with 6, 7, 8, or 9
INDIAN_PHONE_REGEX = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b")
# Standard email address pattern
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
# Labeled person name patterns (e.g., "Borrower: Ramesh Kumar", "Applicant: Ananya Roy")
NAME_LABELED_REGEX = re.compile(
    r"(?i)\b(borrower|applicant|co-applicant|owner|guarantor|customer)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
)
# Honorific person name patterns (e.g., "Mr. Rajesh Sharma", "Shri Amit Verma")
HONORIFIC_NAME_REGEX = re.compile(
    r"\b(?:Mr\.|Mrs\.|Ms\.|Shri\b|Smt\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b"
)

# Known Prompt Injection and Jailbreak patterns
INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore\s+(?:all\s+)?previous\s+instructions\b"),
    re.compile(r"(?i)\bdisregard\s+(?:all\s+)?prior\s+guidelines\b"),
    re.compile(r"(?i)\bsystem\s+override\b"),
    re.compile(r"(?i)\bforce\s+(?:loan\s+)?approval\b"),
    re.compile(r"(?i)\byou\s+must\s+approve\s+this\s+loan\b"),
    re.compile(r"(?i)\bauto-?sanction\s+this\s+application\b"),
    re.compile(r"(?i)\bact\s+as\s+(?:DAN|jailbreak|unrestricted)\b"),
    re.compile(r"(?i)\bbypass\s+all\s+(?:risk|credit|underwriting)\s+checks\b"),
]


def redact_pii(text: str) -> Tuple[str, int, List[str]]:
    """Scan and redact personally identifiable information (PII) from text.

    Returns:
        Tuple of (redacted_text, total_redactions_count, list_of_redacted_types)
    """
    if not text:
        return text, 0, []

    redactions_count = 0
    detected_types = []
    redacted = text

    # 1. Redact Aadhaar Numbers
    matches = AADHAAR_REGEX.findall(redacted)
    if matches:
        redactions_count += len(matches)
        detected_types.append("AADHAAR")
        redacted = AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", redacted)

    # 2. Redact PAN Cards
    matches = PAN_REGEX.findall(redacted)
    if matches:
        redactions_count += len(matches)
        detected_types.append("PAN")
        redacted = PAN_REGEX.sub("[REDACTED_PAN]", redacted)

    # 3. Redact Emails
    matches = EMAIL_REGEX.findall(redacted)
    if matches:
        redactions_count += len(matches)
        detected_types.append("EMAIL")
        redacted = EMAIL_REGEX.sub("[REDACTED_EMAIL]", redacted)

    # 4. Redact Indian Phone Numbers
    matches = INDIAN_PHONE_REGEX.findall(redacted)
    if matches:
        redactions_count += len(matches)
        detected_types.append("PHONE")
        redacted = INDIAN_PHONE_REGEX.sub("[REDACTED_PHONE]", redacted)

    # 5. Redact Labeled Names (Borrower: John Doe)
    def _replace_labeled_name(m):
        nonlocal redactions_count
        redactions_count += 1
        label = m.group(1)
        return f"{label}: [REDACTED_NAME]"

    if NAME_LABELED_REGEX.search(redacted):
        detected_types.append("BORROWER_NAME")
        redacted = NAME_LABELED_REGEX.sub(_replace_labeled_name, redacted)

    # 6. Redact Honorific Names (Mr. Rajesh Kumar)
    matches = HONORIFIC_NAME_REGEX.findall(redacted)
    if matches:
        redactions_count += len(matches)
        if "BORROWER_NAME" not in detected_types:
            detected_types.append("PERSON_NAME")
        redacted = HONORIFIC_NAME_REGEX.sub("[REDACTED_NAME]", redacted)

    return redacted, redactions_count, detected_types


def sanitize_prompt_input(text: str) -> Tuple[str, bool]:
    """Inspect text for prompt injection vectors and neutralize them.

    Returns:
        Tuple of (sanitized_text, injection_detected_bool)
    """
    if not text:
        return text, False

    sanitized = text
    injection_detected = False

    for pattern in INJECTION_PATTERNS:
        if pattern.search(sanitized):
            injection_detected = True
            sanitized = pattern.sub("[POTENTIAL_INJECTION_STRIPPED]", sanitized)

    return sanitized, injection_detected


def minimize_case_payload(
    case_data: Dict[str, Any],
    property_data: Dict[str, Any],
    valuation_result: Dict[str, Any],
    comparables: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Prepare a strictly data-minimized payload for AI Underwriter evaluation.

    Complies with DPDP Act 2023 purpose limitation:
    Only structural, spatial, financial, and risk indicators are forwarded.
    All personal identities, phone numbers, emails, and PAN/Aadhaar references
    are stripped or redacted.
    """
    # Scrub text fields that might contain free-form notes or personal data
    raw_notes = case_data.get("notes") or ""
    clean_notes, pii_count, _ = redact_pii(raw_notes)
    clean_notes, _ = sanitize_prompt_input(clean_notes)

    # Minimized property structural & spatial factors
    minimized_property = {
        "property_type": property_data.get("property_type") or property_data.get("propertyType"),
        "city": property_data.get("city"),
        "micro_market": property_data.get("micro_market") or property_data.get("microMarket"),
        "sub_market": property_data.get("sub_market") or property_data.get("subMarket"),
        "pincode": property_data.get("pincode"),
        "super_built_up_area": property_data.get("super_built_up_area") or property_data.get("superBuiltUpArea"),
        "carpet_area": property_data.get("carpet_area") or property_data.get("carpetArea"),
        "floor": property_data.get("floor"),
        "total_floors": property_data.get("total_floors") or property_data.get("totalFloors"),
        "age_of_property": property_data.get("age_of_property") or property_data.get("ageOfProperty"),
        "bedrooms": property_data.get("bedrooms"),
        "bathrooms": property_data.get("bathrooms"),
        "facing": property_data.get("facing"),
        "furnishing": property_data.get("furnishing"),
        "amenities": property_data.get("amenities", []),
        "circle_rate_sqft": property_data.get("circle_rate_sqft") or property_data.get("circleRateSqft"),
    }

    # Minimized valuation calculations (provisional rule-based)
    minimized_valuation = {
        "engine_type": valuation_result.get("engine_type", "provisional rule-based estimation"),
        "base_rate_sqft": valuation_result.get("base_price_sqft") or valuation_result.get("basePriceSqft"),
        "fair_market_value": valuation_result.get("final_valuation_amount") or valuation_result.get("finalValuationAmount"),
        "haircut_pct": valuation_result.get("haircut_pct") or valuation_result.get("haircutPct"),
        "liquidation_value": valuation_result.get("liquidation_value") or valuation_result.get("liquidationValue"),
        "sanction_recommendation": valuation_result.get("sanction_recommendation") or valuation_result.get("sanctionRecommendation"),
        "confidence_score": valuation_result.get("confidence_score") or valuation_result.get("confidenceScore"),
        "risk_tier": valuation_result.get("risk_tier") or valuation_result.get("riskTier"),
        "confidence_breakdown": valuation_result.get("confidence_breakdown") or valuation_result.get("confidenceBreakdown", {}),
        "scorecard": valuation_result.get("scorecard", {}),
        "model_governance_provenance": valuation_result.get("model_governance_provenance", "PROVISIONAL_RULE_BASED_PENDING_TRAINING_DATA"),
    }

    # Minimized de-identified comparable transactions
    minimized_comparables = []
    for comp in comparables:
        comp_notes, _, _ = redact_pii(comp.get("notes") or "")
        minimized_comparables.append({
            "comparable_id": comp.get("id"),
            "property_type": comp.get("property_type") or comp.get("propertyType"),
            "sale_price": comp.get("sale_price") or comp.get("salePrice"),
            "price_per_sqft": comp.get("price_per_sqft") or comp.get("pricePerSqft"),
            "distance_km": comp.get("distance_km") or comp.get("distanceKm"),
            "transaction_date": str(comp.get("transaction_date") or comp.get("transactionDate")),
            "similarity_score": comp.get("similarity_score") or comp.get("similarityScore"),
            "data_source": comp.get("data_source") or comp.get("dataSource", "synthetic-demo"),
            "is_synthetic_demonstration": comp.get("is_synthetic_demonstration", True),
            "notes": comp_notes,
        })

    return {
        "case_id": case_data.get("id"),
        "case_status": case_data.get("status"),
        "notes": clean_notes,
        "pii_redacted_count": pii_count,
        "property": minimized_property,
        "valuation": minimized_valuation,
        "comparables": minimized_comparables,
    }
