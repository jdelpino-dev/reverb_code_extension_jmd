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
# testable boundaries without over-engineering into ports/adapters/hexagonal.
#
# TODO: Refactor for consistency — categories uses _load_categories() as a
# service helper, but listings calls ReverbClient directly. Add _load_listings()
# to establish a consistent service boundary (pagination, caching, etc. will
# go there).

from flask import Flask, request, render_template
from reverb_client import ReverbClient
app = Flask(__name__)

@app.route('/')
@app.route('/categories')
def categories():
  categories = _search_categories(request.args.get('query'))
  return render_template('categories.html', categories=categories)

@app.route('/listings')
def listings():
  # TODO: Inconsistent — calls ReverbClient directly instead of going through
  # a _load_listings() helper like categories does. Add _load_listings() for
  # consistency and to support future pagination/filtering.
  return render_template('listings.html', listings=ReverbClient().listings())

def _search_categories(query):
  if not query: return []

  categories = _load_categories()
  return filter(lambda c: query.lower() in c['full_name'].lower(), categories)

# NOTE: Thin wrapper now, but this is the right place to add pagination,
# caching, or response normalization later.
def _load_categories():
  return ReverbClient().categories()

# TODO: Add _load_listings() for consistency.