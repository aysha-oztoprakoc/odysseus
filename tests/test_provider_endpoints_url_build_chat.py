"""Provider endpoint URL-building tests: build_chat_url."""
import pytest

from src import endpoint_resolver as er


@pytest.fixture
def no_dns(monkeypatch):
    """Neutralize resolve_url so URL-building tests never touch DNS/Tailscale.

    build_chat_url/build_models_url call the module-global resolve_url first;
    patching it on the module makes those calls a no-op (functions resolve
    globals by name at call time).
    """
    monkeypatch.setattr(er, "resolve_url", lambda u: u)


# (id, base_url, expected_chat_url)
PROVIDER_CASES = [
    ("openai", "https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
    ("openai_pathless", "https://api.openai.com", "https://api.openai.com/v1/chat/completions"),
    ("anthropic", "https://api.anthropic.com", "https://api.anthropic.com/v1/messages"),
    # Anthropic base that already carries /v1 must not become /v1/v1/messages.
    ("anthropic_v1", "https://api.anthropic.com/v1", "https://api.anthropic.com/v1/messages"),
    ("openrouter", "https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1/chat/completions"),
    ("groq", "https://api.groq.com/openai/v1", "https://api.groq.com/openai/v1/chat/completions"),
    ("nvidia", "https://integrate.api.nvidia.com/v1", "https://integrate.api.nvidia.com/v1/chat/completions"),
    ("xai", "https://api.x.ai/v1", "https://api.x.ai/v1/chat/completions"),
    ("deepseek", "https://api.deepseek.com", "https://api.deepseek.com/chat/completions"),
    # Gemini's OpenAI-compatible surface — treated as a generic OpenAI endpoint.
    ("gemini_openai", "https://generativelanguage.googleapis.com/v1beta/openai", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
    ("ollama_local", "http://localhost:11434/api", "http://localhost:11434/api/chat"),
    ("ollama_cloud", "https://ollama.com", "https://ollama.com/api/chat"),
]


@pytest.mark.parametrize(
    "base,expected", [(c[1], c[2]) for c in PROVIDER_CASES],
    ids=[c[0] for c in PROVIDER_CASES],
)
def test_build_chat_url(no_dns, base, expected):
    assert er.build_chat_url(base) == expected


def test_chat_url_never_double_prefixes_anthropic(no_dns):
    """Regression guard: the /v1 collapse must not produce /v1/v1/messages."""
    url = er.build_chat_url("https://api.anthropic.com/v1")
    assert "/v1/v1/" not in url
    assert url.count("/v1/messages") == 1
