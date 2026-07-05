from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""

    parsed = urlparse(value if "://" in value else f"//{value}")
    domain = (parsed.netloc or parsed.path.split("/", 1)[0]).lower()
    if domain.startswith("www."):
        domain = domain[4:]

    path = parsed.path if parsed.netloc else ""
    normalized = f"{domain}{path}".rstrip("/")
    return normalized


def extract_domain(url: str) -> str:
    value = normalize_url(url)
    return value.split("/", 1)[0] if value else ""


def normalize_domain(url_or_domain: str) -> str:
    return extract_domain(url_or_domain)
