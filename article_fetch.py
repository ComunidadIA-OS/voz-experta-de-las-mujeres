"""Get the headline, introduction, body and licence of a news article from its link.

trafilatura finds the main text of most news pages. The licence is read from the
page itself: a link to a Creative Commons licence, or a rights line of the article
such as "Derechos: Creative Commons".
Nothing is saved: the text only lives in the app session.
"""

import re
from urllib.parse import urlparse

import requests

USER_AGENT = "Mozilla/5.0 (open-source tool Voz experta de las mujeres)"

# creativecommons.org/licenses/by/4.0/ -> CC BY 4.0
CC_LINK = re.compile(r"creativecommons\.org/licenses/([a-z-]+)/(\d\.\d)", re.IGNORECASE)
CC_PUBLIC_DOMAIN = re.compile(r"creativecommons\.org/publicdomain/zero/(\d\.\d)", re.IGNORECASE)
# A rights line of the article itself, such as "Derechos: Creative Commons" or "Licencia: CC BY".
# Site-wide banners without that label are ignored: they appear on every page,
# also on articles from news agencies with all rights reserved.
CC_RIGHTS_LINE = re.compile(
    r"(?:Derechos|Licencia|Drets|Llicència|License|Rights)\s*:\s*(?:<[^>]+>\s*)*(?:Creative\s+Commons|CC[\s-]BY)",
    re.IGNORECASE,
)


class ArticleNotFound(Exception):
    """The page could not be read: wrong link, paywall, or a site that blocks automatic access."""


def detect_licence(html):
    """Return the Creative Commons licence the page declares, such as "CC BY 4.0", or None."""
    match = CC_LINK.search(html)
    if match:
        return f"CC {match.group(1).upper()} {match.group(2)}"
    match = CC_PUBLIC_DOMAIN.search(html)
    if match:
        return f"CC0 {match.group(1)}"
    if CC_RIGHTS_LINE.search(html):
        return "Creative Commons"
    return None


def fetch_article(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ArticleNotFound("El enlace no es válido.")

    import trafilatura

    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
    except requests.RequestException as error:
        raise ArticleNotFound("No se ha podido abrir la página.") from error

    document = trafilatura.bare_extraction(response.text, url=url, with_metadata=True)
    if document is None:
        raise ArticleNotFound("No se ha encontrado el texto de la noticia en la página.")
    data = document if isinstance(document, dict) else document.as_dict()
    paragraphs = [p.strip() for p in (data.get("text") or "").split("\n") if p.strip()]
    if len(" ".join(paragraphs)) < 300:
        raise ArticleNotFound("La página tiene muy poco texto: puede estar tras un muro de pago.")
    # "Headline | Site name": keep the headline only.
    headline = re.sub(r"\s+\|\s+[^|]{2,60}$", "", (data.get("title") or "").strip())
    if paragraphs and paragraphs[0].strip() == headline:
        paragraphs = paragraphs[1:]
    return {
        "headline": headline,
        "introduction": data.get("description") or "",
        "body": "\n".join(paragraphs),
    }, detect_licence(response.text)
