"""Provider classification from a base URL: _provider_label."""
import pytest

from src.llm_core import _provider_label


# ── _provider_label ──
# Human-friendly name used in error/degraded-state messages.

class TestProviderLabel:
    @pytest.mark.parametrize("url,expected", [
        ("https://api.anthropic.com/v1", "Anthropic"),
        ("https://ollama.com", "Ollama Cloud"),
        ("https://api.x.ai/v1", "xAI"),
        ("https://api.openai.com/v1", "OpenAI"),
        ("https://openrouter.ai/api/v1", "OpenRouter"),
        ("https://api.groq.com/openai/v1", "Groq"),
        ("https://integrate.api.nvidia.com/v1", "NVIDIA"),
        ("https://api.mistral.ai/v1", "Mistral"),
        ("https://api.deepseek.com", "DeepSeek"),
        ("https://generativelanguage.googleapis.com/v1beta/openai", "Google"),
        ("https://api.together.xyz/v1", "Together"),
        ("https://api.together.ai/v1", "Together"),
        ("https://api.fireworks.ai/inference/v1", "Fireworks"),
        ("http://localhost:11434/api", "Ollama"),
    ])
    def test_known_labels(self, url, expected):
        assert _provider_label(url) == expected

    @pytest.mark.parametrize("url", [
        "http://localhost:8080/v1",
        "http://127.0.0.1:8080/v1",
        "http://localhost:8000/v1",
        "http://localhost:1234/v1",
        "http://localhost:9999/v1",
    ])
    def test_local_non_ollama_endpoint(self, url):
        # The serving tool is NOT inferred from the port: vLLM, SGLang, llama.cpp
        # and plain OpenAI-compatible servers all share 8000/8080, so a port-only
        # label would mislabel real setups. The tool is identified by /props
        # fingerprinting during discovery; this helper stays neutral.
        assert _provider_label(url) == "local endpoint"

    def test_unknown_host_returns_host(self):
        assert _provider_label("https://api.unknown-llm.example/v1") == "api.unknown-llm.example"

    @pytest.mark.parametrize("url", ["", None])
    def test_empty_returns_generic(self, url):
        assert _provider_label(url) == "provider"
