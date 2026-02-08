"""Tests for Exist.io API client."""

import json

import pytest
import responses

from exist_backup.api import BASE_URL, ExistClient


@pytest.fixture
def client():
    return ExistClient("test-token-123")


class TestExistClient:
    @responses.activate
    def test_get_profile(self, client):
        responses.add(
            responses.GET,
            BASE_URL + "accounts/profile/",
            json={"username": "testuser", "timezone": "US/Eastern"},
            status=200,
        )
        profile = client.get_profile()
        assert profile["username"] == "testuser"
        assert "Token test-token-123" in responses.calls[0].request.headers["Authorization"]

    @responses.activate
    def test_get_attributes_pagination(self, client):
        page1 = {
            "count": 3,
            "next": BASE_URL + "attributes/?page=2&limit=2",
            "previous": None,
            "results": [
                {"attribute": "steps", "label": "Steps"},
                {"attribute": "sleep", "label": "Sleep"},
            ],
        }
        page2 = {
            "count": 3,
            "next": None,
            "previous": BASE_URL + "attributes/?page=1&limit=2",
            "results": [
                {"attribute": "mood", "label": "Mood"},
            ],
        }
        responses.add(responses.GET, BASE_URL + "attributes/", json=page1, status=200)
        responses.add(responses.GET, BASE_URL + "attributes/?page=2&limit=2", json=page2, status=200)

        attrs = client.get_attributes()
        assert len(attrs) == 3
        assert attrs[0]["attribute"] == "steps"
        assert attrs[2]["attribute"] == "mood"

    @responses.activate
    def test_get_attribute_values(self, client):
        responses.add(
            responses.GET,
            BASE_URL + "attributes/values/",
            json={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {"date": "2024-12-01", "value": "8432"},
                    {"date": "2024-12-02", "value": "6201"},
                ],
            },
            status=200,
        )
        values = list(client.get_attribute_values("steps", date_max="2024-12-02"))
        assert len(values) == 2
        assert values[0]["value"] == "8432"

    @responses.activate
    def test_rate_limit_retry(self, client):
        responses.add(
            responses.GET,
            BASE_URL + "accounts/profile/",
            json={"detail": "Request was throttled."},
            status=429,
            headers={"Retry-After": "1"},
        )
        responses.add(
            responses.GET,
            BASE_URL + "accounts/profile/",
            json={"username": "testuser"},
            status=200,
        )
        profile = client.get_profile()
        assert profile["username"] == "testuser"
        assert len(responses.calls) == 2

    @responses.activate
    def test_http_error_raised(self, client):
        responses.add(
            responses.GET,
            BASE_URL + "accounts/profile/",
            json={"detail": "Not found"},
            status=404,
        )
        with pytest.raises(Exception):
            client.get_profile()
