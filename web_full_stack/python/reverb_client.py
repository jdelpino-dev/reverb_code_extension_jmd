import requests


class ReverbClient:
    HEADERS = {
        "Accept": "application/hal+json",
        "Accept-Version": "3.0",
        "Content-Type": "application/hal+json",
    }

    def __init__(self, base_uri="https://api.reverb.com/api"):
        self._base_uri = base_uri

    def listings(self, per_page=10):
        return self._get("/listings/all", {"per_page": per_page})["listings"]

    def categories(self):
        # ERROR HANDLING: KeyError is possible here but it is propagated and catch on
        # the service layer.
        return self._get("/categories/flat")["categories"]

    # Fixed a BUG prone pattern: mutable parameters: params={} _> params=None, and
    # ensure params is always a dictionary and a different one per request.
    def _get(self, path, params=None):
        if params is None:
            params = {}  # fresh allocated dict at call time.
        response = requests.get(
            self._base_uri + path,
            headers=self.HEADERS,
            params=params,
            # NOTE: Enhancement: timeout: (connect_timeout, read_timeout)
            timeout=(
                3,
                5,
            ),
        )
        response.raise_for_status()  # raises HTTPError (subclass of RequestException) for 4xx/5xx
        return response.json()  # only called on 2xx — less likely to return HTML
