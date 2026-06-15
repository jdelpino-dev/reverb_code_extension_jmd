from unittest.mock import patch

CATEGORIES = [
    {"full_name": "Guitars"},
    {"full_name": "Drums"},
]


def test_no_search_term_shows_form_and_no_categories(client):
    response = client.get("/categories")

    assert response.status_code == 200
    assert b'name="search"' in response.data
    assert b'type="submit"' in response.data
    assert b"Guitars" not in response.data


def test_search_matching_categories_displays_them(client):
    with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
        response = client.get("/categories?search=guitar")

    assert response.status_code == 200
    assert b"Guitars" in response.data
    assert b"Drums" not in response.data
    assert b'value="guitar"' in response.data


def test_search_is_case_insensitive(client):
    with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
        response = client.get("/categories?search=GUITAR")

    assert b"Guitars" in response.data
    assert b'class="category-card"' in response.data


def test_no_matching_categories_shows_empty_state(client):
    with patch("app.routes.categories.reverb.categories", return_value=CATEGORIES):
        response = client.get("/categories?search=violin")

    assert response.status_code == 200
    assert b"No categories found" in response.data
    assert b"violin" in response.data
    assert b'class="category-card"' not in response.data


def test_root_route_renders_categories(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'name="search"' in response.data
