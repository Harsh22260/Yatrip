"""
Cafe (and food place) photographs from Wikimedia Commons / Wikipedia.

OSM carries an ``image`` tag but cafes almost never use it, and the tag set it
does use is wider than the single key the importer used to read. So there are two
sources here:

1. the OSM tag family, handled in ``osm_food_service._parse_image``
2. a name lookup, reused from the attraction image service

The honest limitation, which is why this is a backfill command and not something
that runs inline: a neighbourhood cafe in a small town frequently has no
photograph on Wikimedia at all. Those rows are left empty and the frontend falls
back to generated category artwork via ``PlaceImage``, so a card is never blank.
An outlet owner supplying their own photo at registration is the reliable path.
"""

from __future__ import annotations

import logging
import re
import time

import requests

from attractions.services.images import _wikipedia_photo, search_photo

logger = logging.getLogger(__name__)

#: Words that carry no identifying information for a cafe, so a matching file
#: name does not have to contain them. A cafe called "Cafe Coffee Day" would
#: otherwise match almost anything.
_STOPWORDS = frozenset(
    {
        "the", "of", "and", "a", "an", "in", "at", "on", "to", "for",
        "cafe", "café", "coffee", "restaurant", "bakery", "dhaba", "hotel",
        "shop", "store", "house", "corner", "point", "centre", "center",
        "byname", "foods", "food", "eatery", "bistro", "bar", "lounge",
    }
)

#: image_url is a 200-char URLField column on some tables and a TextField here,
#: but Commons thumbnail URLs with a long file name can still exceed what is
#: worth storing. Anything longer is discarded rather than truncated.
_MAX_URL_LEN = 300


def _tokens(name: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def find_food_photo(place_name: str, city: str = "", session: requests.Session | None = None) -> dict | None:
    """
    One usable photograph for a cafe, or ``None``.

    ``None`` is the common case for a small-town cafe and is not an error; the
    caller falls back to generated artwork.
    """
    place_name = (place_name or "").strip()
    if not place_name or not _tokens(place_name):
        return None

    queries = []
    if city:
        queries.append(f"{place_name} {city}")
    queries.append(place_name)

    # The city is part of what has to match, not just part of the query. Chains
    # and similarly named cafes repeat across cities, and "Blue Tokai, Delhi"
    # otherwise happily takes a photograph of a shopping mall in Cape Town: the
    # name matched, the geography did not.
    require = f"{place_name} {city}".strip()

    for query in queries:
        found = search_photo(query, require=require, session=session) or _wikipedia_photo(
            query, require=require, session=session
        )
        if found:
            if len(found["url"]) > _MAX_URL_LEN:
                logger.info("discarding over-long image url for %r", place_name)
                return None
            return found
    return None


def backfill(
    queryset,
    *,
    only_missing: bool = True,
    categories: tuple[str, ...] | None = None,
    limit: int | None = None,
    session: requests.Session | None = None,
    delay: float = 0.4,
) -> dict[str, int]:
    """
    Fill ``image_url`` for the cafes in ``queryset``.

    Sequential with a pause: Commons is a shared free service and a burst of
    hundreds of searches gets the address throttled. Meant to be run from the
    management command or a background job, never inside a web request.
    """
    qs = queryset
    if categories:
        qs = qs.filter(category__in=categories)
    # Take the rows before the caller slices: Django refuses further filtering
    # once a slice exists.
    rows = list(qs.order_by("-rating", "name")[:limit] if limit else qs.order_by("-rating", "name"))

    if only_missing:
        rows = [r for r in rows if not (r.image_url or "").strip()]

    s = session or requests.Session()
    stats = {"filled": 0, "no_match": 0, "failed": 0}

    for i, row in enumerate(rows, 1):
        found = find_food_photo(row.name, row.city, session=s)
        if not found:
            stats["no_match"] += 1
            logger.info("no photograph for %r (%s)", row.name, row.city)
        else:
            # update() so a concurrent description or rating edit is not clobbered
            # by an image backfill.
            updated = type(row).objects.filter(pk=row.pk).update(
                image_url=found["url"], image_credit=found["credit"]
            )
            if updated:
                stats["filled"] += 1
            else:
                stats["failed"] += 1
        if i % 25 == 0:
            logger.info("food images: %d/%d processed", i, len(rows))
        time.sleep(delay)

    return stats