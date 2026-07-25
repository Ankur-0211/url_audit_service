from bs4 import BeautifulSoup
import httpx

SECURITY_HEADERS = {
    "strict_transport_security": "strict-transport-security",
    "content_security_policy": "content-security-policy",
    "x_content_type_options": "x-content-type-options",
    "x_frame_options": "x-frame-options",
}


def analyze_headers(response: httpx.Response) -> dict:
    return {
        key: header_name in response.headers
        for key, header_name in SECURITY_HEADERS.items()
    }


def analyze_html(content_type: str | None, body: bytes) -> dict:
    """Pure function — no I/O. Returns title, meta_description, h1_count."""
    if not content_type or "text/html" not in content_type:
        return {"title": None, "meta_description": None, "h1_count": 0}

    soup = BeautifulSoup(body, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag.get("content") if meta_tag else None

    h1_count = len(soup.find_all("h1"))

    return {
        "title": title,
        "meta_description": meta_description,
        "h1_count": h1_count,
    }
