"""
JWT delivered in cookies rather than in JavaScript-readable storage.

The reason to prefer cookies here is specific: with the access token in
``localStorage`` any script that manages to run on the page — a stored XSS, a
compromised dependency, a malicious browser extension — can read the token and
call the API as the user for the next five hours. An ``HttpOnly`` cookie is
attached by the browser automatically and cannot be read back by that script.

The trade-off is CSRF, because a cookie is sent whether or not the page asked
for it. That is handled by two things working together:

* ``SameSite=Lax`` on the cookies, which blocks cross-site POSTs in every
  current browser while still allowing normal top-level navigation.
* Django's CSRF check, which the frontend satisfies by echoing the
  ``csrftoken`` cookie back in the ``X-CSRFToken`` header.

SimpleJWT's stock authentication only understands the ``Authorization`` header,
so this subclasses it to also read the cookie. The header path is left in place
so the test client and any CLI usage keep working.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

#: Cookie names. Deliberately not prefixed ``__Host-``: that prefix demands
#: Secure and Path=/, which breaks plain-HTTP local development, and this app
#: is routinely run on http://localhost.
ACCESS_COOKIE = "yatrip_access"
REFRESH_COOKIE = "yatrip_refresh"


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate from the access cookie, falling back to the header."""

    def authenticate(self, request):
        raw = request.COOKIES.get(ACCESS_COOKIE)
        if not raw:
            # No cookie: let the next authenticator (the header) try.
            return super().authenticate(request)

        # The cookie holds a bare access token, which is exactly what the
        # inherited get_validated_token expects, so no re-implementation is
        # needed. An expired cookie raises InvalidToken, which DRF turns into
        # a 401 — correct, and the frontend then calls refresh.
        validated_token = self.get_validated_token(raw)
        return self.get_user(validated_token), validated_token


def set_auth_cookies(
    response, access: str, refresh: str | None = None, request=None
) -> None:
    """
    Attach the tokens as HttpOnly cookies.

    ``secure`` follows DEBUG so that development over plain HTTP still logs in,
    but it must be True in production or the cookie would travel in clear text.
    """
    common = {
        "httponly": True,
        "samesite": "Lax",
        "secure": not settings.DEBUG,
        "path": "/",
    }
    max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(ACCESS_COOKIE, access, max_age=max_age, **common)

    if refresh:
        refresh_max = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        response.set_cookie(REFRESH_COOKIE, refresh, max_age=refresh_max, **common)

    # Readable by JS on purpose: this one holds no authority, it exists only so
    # the SPA can send it back in the X-CSRFToken header.
    if request is not None:
        response.set_cookie(
            "csrftoken",
            get_token(request),
            max_age=max_age,
            httponly=False,
            samesite="Lax",
            secure=not settings.DEBUG,
            path="/",
        )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
