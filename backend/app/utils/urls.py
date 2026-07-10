from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""

    parsed = urlparse(value if "://" in value else f"//{value}")
    host = (parsed.hostname or parsed.netloc or parsed.path.split("/", 1)[0]).lower()
    if host.startswith("www."):
        host = host[4:]
    port = ""
    if parsed.port and not (
        (parsed.scheme == "http" and parsed.port == 80)
        or (parsed.scheme == "https" and parsed.port == 443)
        or (not parsed.scheme and parsed.port in {80, 443})
    ):
        port = f":{parsed.port}"
    domain = f"{host}{port}"

    path = parsed.path if parsed.netloc else ""
    normalized = f"{domain}{path}".rstrip("/")
    return normalized


def extract_domain(url: str) -> str:
    value = normalize_url(url)
    return value.split("/", 1)[0] if value else ""


def normalize_domain(url_or_domain: str) -> str:
    return extract_domain(url_or_domain)
