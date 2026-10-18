"""Shared helpers for turning raw scraped text into clean price floats."""
import re

PRICE_PATTERN = re.compile(r"(\d+(?:\.\d{1,2})?)")


def parse_price_text(text: str):
    """Extracts a price as a float from messy scraped text, e.g. '$8.50', '$12.00 each',
    '8.5'. Returns None if no number is found."""
    if not text:
        return None
    cleaned = text.replace(",", "")
    match = PRICE_PATTERN.search(cleaned)
    if not match:
        return None
    return float(match.group(1))
