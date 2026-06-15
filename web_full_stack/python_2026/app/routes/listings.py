from flask import Blueprint, render_template

from app.clients import reverb

listings_bp = Blueprint("listings", __name__)


@listings_bp.route("/listings")
def index():
    return render_template("listings/index.html", listings=reverb.listings())
