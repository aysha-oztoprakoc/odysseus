"""Provider endpoint URL-building tests: build_models_url."""
import pytest

from src import endpoint_resolver as er


@pytest.fixture
def no_dns(monkeypatch):
    """Neutralize resolve_url so URL-building tests never touch DNS/Tailscale."""
    monkeypatch.setattr(er, "resolve_url", lambda u: u)


# (id, base_url, expected_models_url)
PROVIDER_CASES = [
    ("openai", "https://api.openai.com/v1", "https://api.openai.com/v1/models"),
    ("openai_pathless", "https://api.openai.com", "https://api.openai.com/v1/models"),
    ("anthropic", "https://api.anthropic.com", "https://api.anthropic.com/v1/models"),
    ("anthropic_v1", "https://api.anthropic.com/v1", "https://api.anthropic.com/v1/models"),
    ("openrouter", "https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1/models"),
    ("groq", "https://api.groq.com/openai/v1", "https://api.groq.com/openai/v1/models"),
    ("nvidia", "https://integrate.api.nvidia.com/v1", "https://integrate.api.nvidia.com/v1/models"),
    ("xai", "https://api.x.ai/v1", "https://api.x.ai/v1/models"),
    ("deepseek", "https://api.deepseek.com", "https://api.deepseek.com/v1/models"),
    ("gemini_openai", "https://generativelanguage.googleapis.com/v1beta/openai", "https://generativelanguage.googleapis.com/v1beta/openai/models"),
    ("ollama_local", "http://localhost:11434/api", "http://localhost:11434/api/tags"),
    ("ollama_cloud", "https://ollama.com", "https://ollama.com/api/tags"),
]


@pytest.mark.parametrize(
    "base,expected", [(c[1], c[2]) for c in PROVIDER_CASES],
    ids=[c[0] for c in PROVIDER_CASES],
)
def test_build_models_url(no_dns, base, expected):
    assert er.build_models_url(base) == expected
