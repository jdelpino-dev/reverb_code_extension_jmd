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

    def listing_detail(self, listing_id):
        return self._get(f"/listings/{listing_id}")

    def categories(self):
        return self._get("/categories/flat")["categories"]

    # Fixed a BUG prone pattern: mutable parameters: params={} _> params=None, and
    # ensure params is always a dictionary and a different one per request.
    def _get(self, path, params=None):
        if params is None:
            params = {}  # fresh allocated dict at call time.
        return requests.get(
            self._base_uri + path, headers=self.HEADERS, params=params
        ).json()
