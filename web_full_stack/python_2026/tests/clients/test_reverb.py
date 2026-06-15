from unittest.mock import MagicMock, patch

import pytest

from app.clients import reverb


@pytest.fixture(autouse=True)
def set_reverb_host(monkeypatch):
    monkeypatch.setenv("REVERB_HOST", "https://api.reverb.test")


def make_mock_response(data):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    return mock


def test_categories_fetches_and_returns_list():
    data = {"categories": [{"full_name": "Guitars"}, {"full_name": "Drums"}]}
    with patch("httpx.get", return_value=make_mock_response(data)) as mock_get:
        result = reverb.categories()

    assert result == [{"full_name": "Guitars"}, {"full_name": "Drums"}]
    mock_get.assert_called_once_with(
        "https://api.reverb.test/api/categories/flat",
        params={},
        headers=reverb.HEADERS,
    )


def test_listings_fetches_and_returns_list():
    data = {"listings": [{"id": i} for i in range(1, 6)]}
    with patch("httpx.get", return_value=make_mock_response(data)) as mock_get:
        result = reverb.listings()

    assert len(result) == 5
    mock_get.assert_called_once_with(
        "https://api.reverb.test/api/listings",
        params={"per_page": 10},
        headers=reverb.HEADERS,
    )


def test_listings_forwards_per_page():
    data = {"listings": [{"id": 1}, {"id": 2}]}
    with patch("httpx.get", return_value=make_mock_response(data)) as mock_get:
        result = reverb.listings(per_page=2)

    assert len(result) == 2
    mock_get.assert_called_once_with(
        "https://api.reverb.test/api/listings",
        params={"per_page": 2},
        headers=reverb.HEADERS,
    )
