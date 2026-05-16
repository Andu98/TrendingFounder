import pytest

from src.config.settings import Settings


@pytest.fixture
def valid_env_vars(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


def test_settings_loads_from_env(valid_env_vars):
    s = Settings()
    assert s.cloudflare_api_token == "test-token"
    assert s.supabase_url == "https://test.supabase.co"
    assert s.lmstudio_base_url == "http://localhost:1234/v1"
    assert s.app_timezone == "Europe/Bucharest"
    assert s.log_level == "INFO"


def test_settings_defaults(valid_env_vars):
    s = Settings()
    assert s.lmstudio_model == "qwen/qwen2.5-vl-7b"


def test_settings_missing_required(monkeypatch):
    for key in ("CLOUDFLARE_API_TOKEN", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ENV_FILE", "nonexistent.env")
    with pytest.raises(Exception):
        Settings(_env_file=None)
