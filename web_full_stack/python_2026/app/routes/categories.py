from flask import Blueprint, render_template, request

from app.clients import reverb

categories_bp = Blueprint("categories", __name__)


@categories_bp.route("/")
@categories_bp.route("/categories")
def index():
    search_term = request.args.get("search", "").strip()
    matched_categories = []

    if search_term:
        matched_categories = [
            c
            for c in reverb.categories()
            if search_term.lower() in (c.get("full_name") or "").lower()
        ]

    return render_template(
        "categories/index.html",
        categories=matched_categories,
        search_term=search_term,
    )
