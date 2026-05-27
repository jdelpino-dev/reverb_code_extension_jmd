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

import os
from dotenv import load_dotenv

from flask import Flask, request, render_template, flash
from reverb_client import ReverbClient

load_dotenv()

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
    elif not categories:
        flash(
            f"The are no category results for you query: {query}. "
            f"Try something different",
            "info",
        )
    return render_template("categories.html", categories=categories)


@app.route("/listings")
def listings():
    return render_template("listings.html", listings=_load_listings())


@app.route("/listings/<string:listing_id>")
def listing_detail(listing_id):
    listing = _load_listing_detail(listing_id)
    return render_template("listing_detail.html", listing=listing)


def _search_categories(query):
    if not query:
        return []

    categories = _load_categories()
    # NOTE: we materialized the filter object into a list. Categories are stable
    # and not too big of a collection. And, also we want to consume them and render them,
    # because they are alreay been filtered.
    return list(filter(lambda c: query.lower() in c["full_name"].lower(), categories))
    # return [c for c in categories if query.lower() in c["full_name"].lower()]


# NOTE: Thin wrapper now, but this is the right place to add pagination,
# caching, or response normalization later.
def _load_categories():
    return ReverbClient().categories()


# NOTE: _load_listings() for consistency. Also, for now, just a thin service layer
def _load_listings():
    listings = ReverbClient().listings()
    for listing in listings:
        listing["slug"] = _get_listing_slug(listing)
    return listings


def _load_listing_detail(listing_id):
    listing = ReverbClient().listing_detail(listing_id)
    if listing:
        listing["accepted_payment_methods"] = [
            method.replace("_", " ").title()
            for method in listing.get("accepted_payment_methods", [])
        ]
    return listing

def _get_listing_slug(listing):
    """Extract human-friendly id+slug from _links.self.href."""
    href = listing["_links"]["self"]["href"]
    return href.rstrip("/").split("/")[-1]
