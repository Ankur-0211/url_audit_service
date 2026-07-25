from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def normalize_url(url: str) -> str:
    """
    Normalizes a URL for use as a cache key:
    - lowercases scheme + host
    - sorts query params
    - strips trailing slash from path (except root "/")
    - drops fragment
    """
    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    path = parts.path
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    query_pairs = sorted(parse_qsl(parts.query, keep_blank_values=True))
    query = urlencode(query_pairs)

    return urlunsplit((scheme, netloc, path, query, ""))
