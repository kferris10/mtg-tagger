"""Tests for the env-var API key fallback workflow."""

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


# ---------- GET /config ----------


class TestConfigRoute:
    def test_config_has_env_key_true(self):
        app, _ = _make_app(env_key="sk-ant-test-key")
        with app.test_client() as c:
            resp = c.get("/config")
            assert resp.status_code == 200
            assert resp.get_json() == {"has_env_key": True}

    def test_config_has_env_key_false(self):
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/config")
            assert resp.status_code == 200
            assert resp.get_json() == {"has_env_key": False}

    def test_config_has_env_key_false_when_whitespace_only(self):
        app, _ = _make_app(env_key="   ")
        with app.test_client() as c:
            resp = c.get("/config")
            assert resp.status_code == 200
            assert resp.get_json() == {"has_env_key": False}


# ---------- POST /analyze — env key fallback ----------


class TestAnalyzeEnvKeyFallback:
    """Verify that /analyze uses the env var when no api_key is in the body."""

    @patch("app.anthropic.Anthropic")
    def test_uses_env_key_when_no_key_in_body(self, MockAnthropic):
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

    @patch("app.anthropic.Anthropic")
    def test_request_key_takes_precedence_over_env(self, MockAnthropic):
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
                    "api_key": "sk-ant-request-key",
                    "card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}.",
                },
            )
            assert resp.status_code == 200
            MockAnthropic.assert_called_once_with(api_key="sk-ant-request-key")

    def test_returns_400_when_no_key_anywhere(self):
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.post(
                "/analyze",
                json={"card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}."},
            )
            assert resp.status_code == 400
            assert "API key is required" in resp.get_json()["error"]

    @patch("app.anthropic.Anthropic")
    def test_empty_string_key_in_body_falls_back_to_env(self, MockAnthropic):
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
                    "api_key": "",
                    "card_data": "Name: Sol Ring. Text: {T}: Add {C}{C}.",
                },
            )
            assert resp.status_code == 200
            MockAnthropic.assert_called_once_with(api_key="sk-ant-env-key")


# ---------- POST /analyze — existing validation still works ----------


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

    def test_index_contains_config_fetch(self):
        """The page should fetch /config to decide whether to show the key field."""
        app, _ = _make_app(env_key="")
        with app.test_client() as c:
            resp = c.get("/")
            assert b"/config" in resp.data

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
            # The JS should try JSON.parse inside a try/catch and fall back
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
