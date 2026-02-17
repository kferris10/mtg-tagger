"""Tests for the MTG Tagger app."""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_app(env_key=""):
    """Import app.py with a controlled ANTHROPIC_API_KEY env var."""
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app, app_module


def _mock_anthropic_response(text):
    """Create a mock Anthropic API response."""
    message = MagicMock()
    message.content = [MagicMock(text=text)]
    return message


# ---------- POST /analyze — authentication ----------


class TestAnalyzeAuthentication:
    """Verify that /analyze handles API keys from multiple sources with correct priority."""

    @patch("app.anthropic.Anthropic")
    def test_uses_user_provided_key(self, MockAnthropic):
        """User-provided API key should be used when present."""
        app, _ = _make_app(env_key="sk-ant-env-key")
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(
            '{"cards": []}'
        )

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={
                    "card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}.",
                    "api_key": "sk-ant-user-key"
                },
            )
            assert resp.status_code == 200
            # Should use user-provided key, not env key
            MockAnthropic.assert_called_once_with(api_key="sk-ant-user-key")

    @patch("app.anthropic.Anthropic")
    @patch("app.os.environ.get")
    def test_uses_env_key_as_fallback(self, mock_env_get, MockAnthropic):
        """Env var API key should be used when no user key provided."""
        # Mock environment to return specific key
        def env_side_effect(key, default=""):
            if key == "ANTHROPIC_API_KEY":
                return "sk-ant-env-key"
            return default
        mock_env_get.side_effect = env_side_effect

        app, _ = _make_app()
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

    @patch("app.anthropic.Anthropic")
    def test_user_key_overrides_env_key(self, MockAnthropic):
        """User-provided key should take priority over env var."""
        app, _ = _make_app(env_key="sk-ant-env-key")
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(
            '{"cards": []}'
        )

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={
                    "card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}.",
                    "api_key": "sk-ant-override-key"
                },
            )
            assert resp.status_code == 200
            # Should use user key, not env var
            MockAnthropic.assert_called_once_with(api_key="sk-ant-override-key")

    @patch("app.os.environ.get")
    def test_returns_401_when_no_api_key(self, mock_env_get):
        """Should return 401 when no API key provided from any source."""
        # Mock environment to return empty string for API key
        def env_side_effect(key, default=""):
            if key == "ANTHROPIC_API_KEY":
                return ""
            return default
        mock_env_get.side_effect = env_side_effect

        app, _ = _make_app()
        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 401
            error = resp.get_json()["error"]
            assert "No API key provided" in error
            assert "ANTHROPIC_API_KEY" in error

    @patch("app.os.environ.get")
    @patch("app.anthropic.Anthropic")
    def test_empty_user_key_falls_back_to_env(self, MockAnthropic, mock_env_get):
        """Empty string for user key should fall back to env var."""
        # Mock environment to return specific key
        def env_side_effect(key, default=""):
            if key == "ANTHROPIC_API_KEY":
                return "sk-ant-env-key"
            return default
        mock_env_get.side_effect = env_side_effect

        app, _ = _make_app()
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(
            '{"cards": []}'
        )

        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={
                    "card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}.",
                    "api_key": ""  # Empty string should be treated as not provided
                },
            )
            assert resp.status_code == 200
            MockAnthropic.assert_called_once_with(api_key="sk-ant-env-key")


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

    def test_index_has_api_key_field(self):
        """The page should contain an API key input field."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            assert b'id="api-key"' in resp.data
            assert b'type="password"' in resp.data

    def test_index_contains_results_structure(self):
        """The page should contain the dashboard layout and sortable results table UI elements."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            html = resp.data
            assert b"dashboard" in html
            assert b"left-panel" in html
            assert b"right-panel" in html
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
            assert b"error-toast" in html


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
