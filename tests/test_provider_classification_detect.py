"""Provider classification from a base URL: _detect_provider."""
import pytest

from src.llm_core import _detect_provider


# ── _detect_provider ──
# Matches on hostname (exact or subdomain), never substring, and falls back to
# the OpenAI-compatible default for everything it doesn't special-case.

class TestDetectProvider:
    @pytest.mark.parametrize("url,expected", [
        ("https://api.anthropic.com", "anthropic"),
        ("https://api.anthropic.com/v1", "anthropic"),
        ("https://anthropic.com/v1", "anthropic"),
        ("https://openrouter.ai/api/v1", "openrouter"),
        ("https://api.groq.com/openai/v1", "groq"),
        ("https://integrate.api.nvidia.com/v1", "nvidia"),
        ("http://localhost:11434/api", "ollama"),
        ("https://ollama.com", "ollama"),
        # xAI, DeepSeek and Gemini's OpenAI-compatible surface are NOT
        # special-cased — they speak the OpenAI dialect, so the generic
        # "openai" path is correct, not a missed provider.
        ("https://api.openai.com/v1", "openai"),
        ("https://api.x.ai/v1", "openai"),
        ("https://api.deepseek.com", "openai"),
        ("https://generativelanguage.googleapis.com/v1beta/openai", "openai"),
        # Ollama's OpenAI-compatible /v1 surface is generic, not native ollama.
        ("http://localhost:11434/v1", "openai"),
    ])
    def test_known_providers(self, url, expected):
        assert _detect_provider(url) == expected

    def test_lookalike_host_is_not_matched(self):
        # Host merely *starts* with the provider domain as a label — a classic
        # substring-match trap (anthropic.com.evil.example is not Anthropic).
        assert _detect_provider("https://anthropic.com.evil.example/v1") == "openai"

    def test_provider_domain_in_path_is_not_matched(self):
        # The provider domain appears only in the path, not the host.
        assert _detect_provider("https://proxy.example.com/anthropic.com/v1") == "openai"

    def test_trailing_dot_host_still_matches(self):
        # A fully-qualified host with a trailing dot is still that host.
        assert _detect_provider("https://api.anthropic.com./v1") == "anthropic"

    @pytest.mark.parametrize("url", ["", None, "not a url", "://broken"])
    def test_unidentifiable_falls_back_to_openai(self, url):
        assert _detect_provider(url) == "openai"
