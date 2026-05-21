# Architecture: Layered (Route → Service → Client)
# ─────────────────────────────────────────────────
# This app follows a simple layered architecture:
#
#   Request → Route (HTTP layer) → Service (app logic) → Client (external IO)
#
# - Routes: Handle HTTP concerns only (params, rendering). Stay thin.
# - Service layer: The _load_* / _search_* helpers. Coordinate client calls
#   with app logic (filtering, pagination, caching). This is the boundary
#   where business rules live.
# - Client: ReverbClient wraps the external API (headers, URLs, parsing).
#
# "Service layer" names the middle layer specifically. The overall pattern
# is just "layered architecture" — the simplest structure that gives you
# testable boundaries without over-engineering
# into ports/adapters/hexagonal.
#
# Refactored for consistency — categories uses _load_categories() as a
# service helper, but listings was calling ReverbClient directly. I added
# _load_listings() to establish a consistent service boundary
# (pagination, caching, etc. will go there).

import logging
import os
from dotenv import load_dotenv

from flask import Flask, request, render_template, flash
from reverb_client import ReverbClient
from requests.exceptions import RequestException

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret")


@app.route("/")
@app.route("/categories")
def categories():
    query = request.args.get("query")
    categories = _search_categories(query)
    if not request.args.get("query"):
        flash(
            "Search using a query string. While the query string "
            "is empty, there will be no search results",
            "warning",
        )
    elif categories is None:
        flash("Could not load categories. Please try again.", "error")
        categories = []
    elif not categories:
        flash(
            f"The are no category results for you query: {query}. "
            f"Try something different",
            "info",
        )
    return render_template("categories.html", categories=categories)


@app.route("/listings")
def listings():
    results = _load_listings()
    if results is None:
        flash("Could not load listings. Please try again", "error")
        results = []
    return render_template("listings.html", listings=results)


def _search_categories(query):
    if not query:
        return []

    categories = _load_categories()
    # NOTE: we materialized the filter object into a list. Categories are stable
    # and not too big of a collection. And, also we want to consume them and render them,
    # because they are alreay been filtered.
    if categories is None:
        return None  # propagate load failure
    return list(filter(lambda c: query.lower() in c["full_name"].lower(), categories))
    # return [c for c in categories if query.lower() in c["full_name"].lower()]


# NOTE: Thin wrapper now, but this is the right place to add pagination,
# caching, or response normalization later.
def _load_categories():
    try:
        categories = ReverbClient().categories()
        # NOTE: DEFENSIVE-TEMP-INLINE VALIDATION: Eventually substitute with Pydantic
        return [c for c in categories if "full_name" in c]
    except RequestException:
        logger.exception("Network error fetching categories from Reverb API")
    except KeyError:
        logger.exception("Unexpected response shape from Reverb API /categories/flat")
    except ValueError:
        logger.exception("Invalid JSON response from Reverb API /categories/flat")


# NOTE: _load_listings() for consistency. Also, for now, just a thin service layer
def _load_listings():
    try:
        return ReverbClient().listings()
    except RequestException:
        logger.exception("Network error fetching listings from Reverb API")
    except KeyError:
        logger.exception("Unexpected response shape from Reverb API /listings/all")
    except ValueError:
        logger.exception("Invalid JSON response from Reverb API /listings/all")
