"""Tests for the MTG Tagger app."""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_app(env_key=""):
    """Import app.py with a controlled ANTHROPIC_API_KEY env var."""
    import app as app_module

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": env_key}):
        importlib.reload(app_module)

    app_module.app.config["TESTING"] = True
    return app_module.app, app_module


def _mock_anthropic_response(text):
    """Create a mock Anthropic API response."""
    message = MagicMock()
    message.content = [MagicMock(text=text)]
    return message


# ---------- POST /analyze — env var required ----------


class TestAnalyzeEnvKey:
    """Verify that /analyze requires the ANTHROPIC_API_KEY env var."""

    @patch("app.anthropic.Anthropic")
    def test_uses_env_key(self, MockAnthropic):
        app, _ = _make_app(env_key="sk-ant-env-key")
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(
            '{"cards": []}'
        )

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 200
            MockAnthropic.assert_called_once_with(api_key="sk-ant-env-key")

    def test_returns_500_when_no_env_key(self):
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 500
            assert "ANTHROPIC_API_KEY" in resp.get_json()["error"]


# ---------- POST /analyze — validation ----------


class TestAnalyzeValidation:
    def test_missing_card_data(self):
        app, _ = _make_app(env_key="sk-ant-env-key")
        with app.test_client() as c:
            resp = c.post("/analyze", json={"card_data": ""})
            assert resp.status_code == 400
            assert "Card data is required" in resp.get_json()["error"]

    def test_non_json_body(self):
        app, _ = _make_app(env_key="sk-ant-env-key")
        with app.test_client() as c:
            resp = c.post("/analyze", data="not json", content_type="text/plain")
            assert resp.status_code in (400, 415)


# ---------- GET / — index page ----------


class TestIndexRoute:
    def test_index_loads(self):
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            assert resp.status_code == 200
            assert b"MTG Tagger" in resp.data

    def test_index_has_no_api_key_field(self):
        """The page should not contain an API key input field."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            assert b'id="api-key"' not in resp.data

    def test_index_contains_results_structure(self):
        """The page should contain the sortable results table UI elements."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            html = resp.data
            assert b'id="results-table"' in html
            assert b'id="raw-toggle"' in html
            assert b'id="raw-json"' in html
            assert b"renderResults" in html
            assert b"results-table" in html
            assert b"sort-header" in html
            assert b"no tagged mechanics" in html

    def test_index_has_string_result_fallback(self):
        """renderResults should handle plain-string results without crashing."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            html = resp.data
            assert b"JSON.parse" in html
            assert b"catch" in html

    def test_index_has_render_error_handling(self):
        """The fetch catch block should distinguish render errors from network errors."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            html = resp.data
            assert b"Error rendering results" in html


# ---------- POST /analyze — response shape ----------


class TestAnalyzeResponseShape:
    """Verify /analyze returns the right shape for the frontend renderResults."""

    @patch("app.anthropic.Anthropic")
    def test_json_result_returned_as_object(self, MockAnthropic):
        """When the API returns valid JSON, result should be a parsed object."""
        app, _ = _make_app(env_key="sk-ant-env-key")
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        api_json = json.dumps({
            "Sol Ring": {"ramp": "S+ Tier"},
            "Savannah Lions": {},
        })
        mock_client.messages.create.return_value = _mock_anthropic_response(api_json)

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data["result"], dict)
            assert "Sol Ring" in data["result"]
            assert data["result"]["Sol Ring"]["ramp"] == "S+ Tier"
            assert data["result"]["Savannah Lions"] == {}

    @patch("app.anthropic.Anthropic")
    def test_json_in_code_fence_parsed_correctly(self, MockAnthropic):
        """When the API wraps JSON in markdown code fences, it should still parse."""
        app, _ = _make_app(env_key="sk-ant-env-key")
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        fenced = '```json\n{"Sol Ring": {"ramp": "S+ Tier"}}\n```'
        mock_client.messages.create.return_value = _mock_anthropic_response(fenced)

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data["result"], dict)
            assert data["result"]["Sol Ring"]["ramp"] == "S+ Tier"

    @patch("app.anthropic.Anthropic")
    def test_non_json_result_returned_as_string(self, MockAnthropic):
        """When the API returns non-JSON text, result should be a raw string."""
        app, _ = _make_app(env_key="sk-ant-env-key")
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(
            "Sorry, I could not parse those cards."
        )

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data["result"], str)
            assert "could not parse" in data["result"]
