import tldextract

extractor = tldextract.TLDExtract(cache_dir=False)


def normalize_domain(raw: str) -> str:
    """Extract the registrable domain from a raw URL or domain string.

    Handles:
        https://www.Example.com/path?x=1  -> example.com
        http://m.example.com              -> example.com (strips common mobile subdomains)
        subdomain.example.com             -> example.com (registrable domain only)
        example.com                       -> example.com
        EXAMPLE.COM                       -> example.com
        www.example.co.uk                 -> example.co.uk

    Uses tldextract for correct public suffix handling (co.uk, com.br, etc.).
    """
    raw = raw.strip().lower()

    if not raw:
        raise ValueError("Empty domain string")

    result = extractor(raw)

    if not result.suffix:
        raise ValueError(f"No valid TLD suffix found in: {raw}")

    if not result.domain:
        raise ValueError(f"Cannot parse domain from: {raw}")

    registrable = f"{result.domain}.{result.suffix}"

    if not registrable or registrable == ".":
        raise ValueError(f"Cannot extract registrable domain from: {raw}")

    return registrable


def build_display_url(normalized: str) -> str:
    """Build a display URL from a normalized domain."""
    return f"https://{normalized}"


def is_known_giant(normalized: str) -> bool:
    from src.config.constants import KNOWN_GIANTS

    return normalized in KNOWN_GIANTS
