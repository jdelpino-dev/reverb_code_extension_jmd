import os

import httpx

HEADERS = {"Accept": "application/json", "Accept-Version": "3.0"}
CATEGORIES_FLAT_PATH = "categories/flat"
LISTINGS_PATH = "listings"


def _get(path, params=None):
    host = os.environ["REVERB_HOST"]
    response = httpx.get(f"{host}/api/{path}", params=params or {}, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def categories():
    return _get(CATEGORIES_FLAT_PATH)["categories"]


def listings(per_page=10):
    return _get(LISTINGS_PATH, {"per_page": per_page})["listings"]
