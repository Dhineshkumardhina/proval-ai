"""Indian currency and monetary transaction amount validation and normalization."""

import math
import re
from typing import Any, Optional, Tuple


def normalize_transaction_amount(raw_val: Any) -> Tuple[Optional[float], Optional[str]]:
    """Validate and normalize transaction amounts into numeric INR.

    Ensures:
    - Positive numeric values.
    - No NaN/Inf values.
    - Resolves Indian monetary denominations (Crore / Lakh / Thousand).
    - Prevents silent rounding errors.

    Returns:
        (amount_inr, error_message)
    """
    if raw_val is None:
        return None, "Transaction amount is missing"

    if isinstance(raw_val, float):
        if math.isnan(raw_val) or math.isinf(raw_val):
            return None, "Transaction amount is NaN or Infinite"
        if raw_val <= 0:
            return None, f"Transaction amount must be strictly positive (got {raw_val})"
        return round(raw_val, 2), None

    if isinstance(raw_val, int):
        if raw_val <= 0:
            return None, f"Transaction amount must be strictly positive (got {raw_val})"
        return float(raw_val), None

    s = str(raw_val).strip()
    if not s or s.lower() in ("nan", "null", "none", "na", ""):
        return None, "Empty transaction amount string"

    # Reject negative signs immediately
    if "-" in s:
        return None, f"Negative transaction amounts are prohibited: '{raw_val}'"

    clean = re.sub(r"[₹$,\s]", "", s).lower()

    try:
        # Match Crores (Cr / Crore / Crores)
        cr_match = re.search(r"^([\d\.]+)\s*(?:cr|crore|crores)$", clean)
        if cr_match:
            val = float(cr_match.group(1)) * 10_000_000.0
            if val <= 0:
                return None, "Amount must be strictly positive"
            return round(val, 2), None

        # Match Lakhs (L / Lac / Lakh / Lakhs)
        lakh_match = re.search(r"^([\d\.]+)\s*(?:l|lac|lacs|lakh|lakhs)$", clean)
        if lakh_match:
            val = float(lakh_match.group(1)) * 100_000.0
            if val <= 0:
                return None, "Amount must be strictly positive"
            return round(val, 2), None

        # Match Thousands (k / thousand / thousands)
        k_match = re.search(r"^([\d\.]+)\s*(?:k|thousand|thousands)$", clean)
        if k_match:
            val = float(k_match.group(1)) * 1_000.0
            if val <= 0:
                return None, "Amount must be strictly positive"
            return round(val, 2), None

        # Direct numeric parse
        num_str = re.sub(r"[^\d\.]", "", clean)
        if not num_str:
            return None, f"Unparseable monetary string: '{raw_val}'"

        val = float(num_str)
        if val <= 0:
            return None, f"Transaction amount must be strictly positive (got {val})"

        # Sanity floor check (Deeds under ₹1,000 are typically nominal/notional registration fee errors)
        if val < 1000.0:
            return None, f"Transaction amount ₹{val:,.2f} is below minimum plausible consideration floor (₹1,000)"

        return round(val, 2), None

    except Exception as e:
        return None, f"Failed to parse monetary amount '{raw_val}': {e}"

