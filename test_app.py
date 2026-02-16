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
