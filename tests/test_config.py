"""Unit tests for core/config.py"""
import json
import os
import tempfile
import pytest
from unittest.mock import patch
from core.config import ConfigManager, CONFIG_PATH, SECRETS_PATH


@pytest.fixture
def tmp_config(tmp_path):
    """Provides a temporary config file path and patches CONFIG_PATH."""
    cfg_path = str(tmp_path / "config.json")
    with patch("core.config.CONFIG_PATH", cfg_path):
        yield cfg_path


@pytest.fixture
def tmp_secrets(tmp_path):
    """Provides a temporary secrets file path and patches SECRETS_PATH."""
    sec_path = str(tmp_path / "secrets.json")
    with patch("core.config.SECRETS_PATH", sec_path):
        yield sec_path


def test_load_json_missing_file(tmp_path):
    result = ConfigManager._load_json(str(tmp_path / "missing.json"))
    assert result == {}


def test_load_json_malformed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ invalid json }", encoding="utf-8")
    result = ConfigManager._load_json(str(bad))
    assert result == {}


def test_save_and_load_json(tmp_path):
    path = str(tmp_path / "data.json")
    data = {"key": "value", "num": 42}
    ConfigManager._save_json(data, path)
    loaded = ConfigManager._load_json(path)
    assert loaded == data


def test_get_language_default(tmp_config):
    with patch("core.config.CONFIG_PATH", tmp_config):
        lang = ConfigManager.get_language()
    assert lang == "ar"


def test_set_and_get_language(tmp_config):
    with patch("core.config.CONFIG_PATH", tmp_config):
        ConfigManager.set_language("en")
        lang = ConfigManager.get_language()
    assert lang == "en"


def test_get_config_value_default(tmp_config):
    with patch("core.config.CONFIG_PATH", tmp_config):
        val = ConfigManager.get_config_value("nonexistent_key", "default_val")
    assert val == "default_val"


def test_set_and_get_config_value(tmp_config):
    with patch("core.config.CONFIG_PATH", tmp_config):
        ConfigManager.set_config_value("test_key", 123)
        val = ConfigManager.get_config_value("test_key")
    assert val == 123


def test_get_secret_default(tmp_secrets):
    with patch("core.config.SECRETS_PATH", tmp_secrets):
        val = ConfigManager.get_secret("missing", "fallback")
    assert val == "fallback"


def test_set_and_get_secret(tmp_secrets):
    with patch("core.config.SECRETS_PATH", tmp_secrets):
        ConfigManager.set_secret("api_key", "my_secret")
        val = ConfigManager.get_secret("api_key")
    assert val == "my_secret"


def test_load_window_state_with_none_values(tmp_config):
    """Test that load_window_state doesn't crash on None/missing w/h values."""
    data = {"windows": {"test": {"maximized": False}}}
    with patch("core.config.CONFIG_PATH", tmp_config):
        ConfigManager._save_json(data, tmp_config)

        class FakeWindow:
            def resize(self, w, h): pass
            def move(self, x, y): pass
            def showMaximized(self): pass

        # Should not raise TypeError
        ConfigManager.load_window_state("test", FakeWindow())


def test_load_window_state_small_dimensions(tmp_config):
    """Test that windows smaller than 100x100 are not restored."""
    data = {"windows": {"test": {"w": 50, "h": 50, "x": 0, "y": 0, "maximized": False}}}
    with patch("core.config.CONFIG_PATH", tmp_config):
        ConfigManager._save_json(data, tmp_config)

        resized = []

        class FakeWindow:
            def resize(self, w, h): resized.append((w, h))
            def move(self, x, y): pass
            def showMaximized(self): pass

        ConfigManager.load_window_state("test", FakeWindow())
        assert len(resized) == 0


def test_project_root_paths():
    """Test that CONFIG_PATH and SECRETS_PATH are absolute paths."""
    assert os.path.isabs(CONFIG_PATH)
    assert os.path.isabs(SECRETS_PATH)
