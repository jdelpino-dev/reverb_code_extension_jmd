from unittest.mock import patch

LISTINGS = [
    {
        "title": "Fender Stratocaster",
        "photos": [{"_links": {"thumbnail": {"href": "https://example.test/photo1.jpg"}}}],
    }
]


def test_listings_returns_200(client):
    with patch("app.routes.listings.reverb.listings", return_value=LISTINGS):
        response = client.get("/listings")

    assert response.status_code == 200


def test_listings_displays_photo_and_title(client):
    with patch("app.routes.listings.reverb.listings", return_value=LISTINGS):
        response = client.get("/listings")

    assert b'class="listings-grid"' in response.data
    assert b'class="listing-card"' in response.data
    assert b"https://example.test/photo1.jpg" in response.data
    assert b"Fender Stratocaster" in response.data
