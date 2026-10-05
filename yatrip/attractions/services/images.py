"""
Attraction images from Wikimedia Commons.

OpenStreetMap carries an ``image`` tag, but it is missing on the large majority
of places: measured across this database, every attraction had an empty
``image_url``. Fetching what does exist is not enough, so the photos are looked
up by name instead.

Commons is used rather than a photo API because it needs no key, has real
photographs of Indian monuments and temples, and publishes the author and licence
alongside each file. Both are kept: an uncredited hotlink is the kind of thing
that gets an app blocked from the source.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

#: A descriptive User-Agent is a Wikimedia requirement, not a courtesy. Requests
#: sent without one are refused or throttled.
USER_AGENT = (
    "Yatrip/1.0 (local travel app; https://github.com/local/yatrip) python-requests"
)

#: Prefer a thumbnail around this width. Cards render at roughly 400px and detail
#: headers at 800px, so this covers both without pulling multi-megabyte originals.
THUMB_WIDTH = 900

#: Files that are maps, coats of arms, logos or plans rather than photographs of
#: the place. Commons search returns plenty of these for Indian monuments, and a
#: locator map as a hero image looks broken.
#: `poster` is in the list for the same reason: a film titled "After Hours" has
#: its poster on Commons, and it is the top result for a cafe of the same name.
_NON_PHOTO = re.compile(
    r"(locator|map|diagram|logo|coat[_ ]of[_ ]arms|flag|icon|banner|"
    r"plan|sketch|drawing|painting|engraving|postcard|scan|seal|"
    r"stamp|signboard|ticket|schedule|poster|cover|bookplate|"
    r"album|ticket|svg|cover)",
    re.I,
)

#: Very small or very wide images tend to be fragments rather than a usable shot.
_MIN_SIZE = (300, 200)

#: Non-image documents. Commons indexes scanned books and journals in File:, and
#: a search for an Indian monument reliably turns up the page in some gazetteer
#: that mentions it. Those are PDFs, not photographs.
_DOCUMENT_EXT = (".pdf", ".djvu", ".svg", ".webm", ".ogv", ".tif", ".tiff")

#: Words that carry no identifying information, so they are not required to
#: appear in a matching file name.
_STOPWORDS = frozenset(
    {
        "the", "of", "and", "a", "an", "in", "at", "on", "to", "for",
        "park", "garden", "temple", "ghat", "ground", "museum", "monument",
        "maidan", "mandir", "shrine", "stadium", "fort", "palace", "lake",
    }
)


def _name_tokens(name: str) -> list[str]:
    """Identifying words of a place name, lowercased."""
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _title_matches(title: str, tokens: list[str]) -> bool:
    """
    Whether a result title really is the place we asked about.

    Every identifying word has to appear, not just one of them. Matching on a
    single word is what put a Cape Town shopping mall under "Blue Tokai, Delhi"
    and a cup of coffee under "Cafe Coffee Day": "blue" and "coffee" were present,
    "tokai" and "day" were not, and the check passed anyway. Commons and Wikipedia
    both do keyword search, so a one-word hit means the term is common, not that
    the file is the right one. A missing photograph is recoverable because the UI
    falls back to generated artwork; a wrong photograph is not.
    """
    if not tokens:
        return False
    words = set(re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).split())
    return all(t in words for t in tokens)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
    return s


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def search_photo(
    query: str,
    *,
    require: str = "",
    session: requests.Session | None = None,
    limit: int = 6,
) -> dict[str, str] | None:
    """
    Find one usable photograph for a place name.

    Returns ``{"url": ..., "credit": ...}`` or ``None`` when Commons has nothing
    suitable. ``None`` is a normal outcome, not an error: many small parks and
    local temples have no photograph anywhere, and the caller falls back to
    generated art rather than storing a broken link.
    """
    query = (query or "").strip()
    if not query:
        return None

    s = session or _session()
    try:
        r = s.get(
            COMMONS_API,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                # filetype:bitmap keeps SVG diagrams and audio out of results.
                # No `filetype:bitmap` here. It was added on the theory that it would
                # filter out diagrams, but it also filters out everything else:
                # measured against this database it dropped results for 7 of the
                # first 10 places, because Commons classifies most photographs of
                # Indian monuments as "Bitmap" only loosely and the keyword search
                # simply stops matching. The non-photo title filter below is the
                # one that works, and it is precise.
                "gsrsearch": query,
                "gsrnamespace": 6,  # File:
                "gsrlimit": str(limit),
                "prop": "imageinfo",
                "iiprop": "url|size|extmetadata",
                f"iiurlwidth": str(THUMB_WIDTH),
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning("commons lookup failed for %r: %s", query, exc)
        return None

    if r.status_code != 200:
        return None
    pages = (r.json() or {}).get("query", {}).get("pages", {}) or {}

    # dict ordering from the API is not relevance order, so rank explicitly.
    candidates = []
    # Commons search is keyword based, not entity based, so it happily returns a
    # scanned gazetteer page for "Shankar Green Park". Requiring every identifying
    # word of the place to appear in the file name is what makes the result
    # trustworthy; without it the app shows a photo of a Buddha under a Jain
    # temple's name, which is worse than the generated placeholder.
    # `require` is the place name alone; the query may also carry the city, which
    # must not be part of the matching requirement.
    tokens = _name_tokens(require or query)
    for index, page in enumerate(pages.values()):
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        title = page.get("title", "")
        if _NON_PHOTO.search(title):
            continue
        if url.lower().split("?")[0].endswith(_DOCUMENT_EXT):
            continue
        haystack = re.sub(r"[^a-z0-9]+", " ", title.lower())
        if not _title_matches(haystack, tokens):
            continue
        width = info.get("width") or 0
        height = info.get("height") or 0
        if width and height:
            if width < _MIN_SIZE[0] or height < _MIN_SIZE[1]:
                continue
            # Reject panoramas and banner crops, which render badly as a card.
            if width / max(height, 1) > 4:
                continue
        candidates.append((index, url, _credit(info.get("extmetadata") or {})))
        if len(candidates) >= limit:
            break

    if not candidates:
        return None
    _idx, url, credit = candidates[0]
    return {"url": url, "credit": credit}


def _wikipedia_photo(
    query: str,
    *,
    require: str = "",
    session: requests.Session | None = None,
) -> dict[str, str] | None:
    """
    Lead image from the matching English Wikipedia article.

    A second source is needed because Commons photographs real monuments well but
    misses small parks, ghats and neighbourhood temples entirely. Wikipedia is
    the reverse: it has an article far more often than Commons has a photo.

    The article title must match the place name, for the same reason the Commons
    lookup checks file names. Without that check the search happily returns
    "DAV College, Kanpur" for a park in Agra and files it under the wrong name.
    """
    require_tokens = _name_tokens(require or query)
    if not require_tokens:
        return None

    s = session or _session()
    try:
        r = s.get(
            WIKIPEDIA_API,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 3,
                "prop": "pageimages",
                "piprop": "original",
                "redirects": 1,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning("wikipedia lookup failed for %r: %s", query, exc)
        return None

    if r.status_code != 200:
        return None
    pages = (r.json() or {}).get("query", {}).get("pages", {}) or {}

    for page in pages.values():
        title = page.get("title", "")
        if not _title_matches(title, require_tokens):
            continue
        url = (page.get("original") or {}).get("source")
        if not url or _NON_PHOTO.search(title):
            continue
        if url.lower().split("?")[0].endswith(_DOCUMENT_EXT):
            continue
        # Wikipedia's file host serves the same free photographs as Commons but
        # under a different licence metadata endpoint, so credit the article.
        return {
            "url": url,
            "credit": f"{title} · Wikipedia",
        }
    return None


def _credit(meta: dict[str, Any]) -> str:
    """Author plus licence, as Commons publishes them."""
    author = _strip_html(
        (meta.get("Artist") or {}).get("value", "")
    ) or _strip_html((meta.get("Credit") or {}).get("value", ""))
    licence = _strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
    # Very long HTML-stripped values are usually galleries, not a person.
    author = re.sub(r"\s+", " ", author)[:120]
    parts = [p for p in (author, licence) if p]
    return " · ".join(parts)[:300]


def backfill(
    queryset,
    *,
    only_missing: bool = True,
    session: requests.Session | None = None,
    delay: float = 0.4,
) -> dict[str, int]:
    """
    Fill in ``image_url`` for every attraction in ``queryset``.

    Sequential with a pause, because Commons is a shared free service and a
    burst of hundreds of searches gets the address throttled. Runs as a
    management command or a background job, never inside a web request.
    """
    import time

    # Callers often pass an already-sliced queryset from a --limit argument, and
    # Django refuses further filtering once a slice exists. Order here instead:
    # take the rows first, then decide which of them need a photograph.
    rows = list(queryset.only("id", "name", "city", "category", "osm_id"))
    if only_missing:
        rows = [
            r
            for r in rows
            if not type(r).objects.filter(pk=r.pk).values_list("image_url", flat=True).first()
        ]

    s = session or _session()
    stats = {"filled": 0, "no_match": 0, "failed": 0}

    for i, row in enumerate(rows, 1):
        # The city is included because Commons categories are heavily
        # disambiguated by location: "City Palace" alone returns palaces from
        # several countries.
        name = row.name
        queries = [f"{name} {row.city}".strip()] if row.city else []
        queries.append(name)

        found = None
        for q in queries:
            found = search_photo(q, require=name, session=s) or _wikipedia_photo(
                q, require=name, session=s
            )
            if found:
                break
            time.sleep(delay)

        if not found:
            stats["no_match"] += 1
            logger.info("no photograph found for %r (%s)", name, row.city)
        elif len(found["url"]) > 200:
            # image_url is a 200-char column. Rather than fail the row, discard
            # the match and let it fall back to artwork: a truncated URL is worse
            # than no image, because it renders as a broken card.
            logger.info(
                "discarding over-long image url for %r (%d chars)",
                name, len(found["url"]),
            )
            stats["no_match"] += 1
        else:
            # update() rather than save() so concurrent edits to a description
            # or rating are not clobbered by an image backfill.
            updated = type(row).objects.filter(pk=row.pk).update(
                image_url=found["url"], image_credit=found["credit"]
            )
            if updated:
                stats["filled"] += 1
            else:
                stats["failed"] += 1
        if i % 25 == 0:
            logger.info("images: %d/%d processed", i, len(rows))
    return stats