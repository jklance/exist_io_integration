"""Exist.io API client with pagination and rate limit handling."""

import sys
import time

import requests

BASE_URL = "https://exist.io/api/2/"
TIMEOUT = 30
DEFAULT_RETRY_AFTER = 60


class ExistClient:
    """Client for the Exist.io API v2."""

    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Token {token}"
        self.session.headers["Accept"] = "application/json"

    def _request(self, url, params=None):
        """Make a GET request with rate limit handling."""
        while True:
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", DEFAULT_RETRY_AFTER))
                print(f"Rate limited, sleeping {retry_after}s...", file=sys.stderr)
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            return resp.json()

    def _paginate(self, url, params=None):
        """Auto-follow pagination, yielding each result item."""
        params = dict(params or {})
        params.setdefault("limit", 100)
        while url:
            data = self._request(url, params)
            yield from data.get("results", [])
            url = data.get("next")
            params = None  # next URL includes query params

    def get_profile(self):
        """Fetch user profile (single object)."""
        return self._request(BASE_URL + "accounts/profile/")

    def get_attributes(self):
        """Fetch all attribute metadata (paginated)."""
        return list(self._paginate(BASE_URL + "attributes/"))

    def get_attributes_with_values(self, days=1, date_max=None):
        """Fetch all attributes with recent values in bulk (paginated).

        Each result includes attribute metadata plus a 'values' array.
        Max 31 days per request.

        Yields individual attribute dicts.
        """
        params = {"days": min(days, 31)}
        if date_max:
            params["date_max"] = str(date_max)
        yield from self._paginate(BASE_URL + "attributes/with-values/", params)

    def get_attribute_values(self, attribute_name, date_max=None, limit=100):
        """Fetch historical values for one attribute (paginated).

        Yields individual value dicts with 'date' and 'value' keys.
        """
        params = {"attribute": attribute_name, "limit": limit}
        if date_max:
            params["date_max"] = str(date_max)
        yield from self._paginate(BASE_URL + "attributes/values/", params)
