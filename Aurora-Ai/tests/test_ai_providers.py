from __future__ import annotations

import json
import sys

from core import ai_providers, bundled_model, llm_client
from memory import config_manager


def test_provider_settings_preserve_existing_keys_and_save_models(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    config_file.write_text(
        json.dumps({"gemini_api_key": "keep-me", "unrelated": "preserved"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_providers, "CONFIG_FILE", config_file)
    monkeypatch.setattr(ai_providers, "ensure_config_dir", lambda: None)

    ai_providers.save_provider_settings(
        "Groq",
        {"Groq": "groq-secret"},
        {"Groq": "custom-model"},
        "http://localhost:11434",
        "llama3.2",
    )

    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert saved["default_ai_provider"] == "Groq"
    assert saved["groq_api_key"] == "groq-secret"
    assert saved["cloud_models"]["Groq"] == "custom-model"
    assert saved["gemini_api_key"] == "keep-me"
    assert saved["unrelated"] == "preserved"


def test_provider_settings_keep_existing_file_when_atomic_replace_fails(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    original = {"gemini_api_key": "keep-me", "unrelated": "preserved"}
    config_file.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(ai_providers, "CONFIG_FILE", config_file)
    monkeypatch.setattr(ai_providers, "ensure_config_dir", lambda: None)

    def fail_replace(*_args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(ai_providers.os, "replace", fail_replace)
    try:
        ai_providers.save_provider_settings("Groq", {}, {}, "", "")
    except OSError:
        pass
    else:
        raise AssertionError("Expected the simulated replacement failure")

    assert json.loads(config_file.read_text(encoding="utf-8")) == original
    assert list(tmp_path.glob(".api_keys.json.*.tmp")) == []


def test_bundled_model_loads_lazily_and_normalizes_tool_calls(tmp_path, monkeypatch):
    model_file = tmp_path / bundled_model.MODEL_FILENAME
    model_file.write_bytes(b"model")
    captured = {}

    class FakeLlama:
        def __init__(self, **kwargs):
            captured["init"] = kwargs

        def create_chat_completion(self, **kwargs):
            captured["request"] = kwargs
            return {"choices": [{"message": {
                "content": "Ready.",
                "tool_calls": [{"id": "tool-1", "function": {
                    "name": "search", "arguments": "{\"query\": \"aurora\"}",
                }}],
            }}]}

    monkeypatch.setattr(bundled_model, "model_path", lambda: model_file)
    monkeypatch.setattr(bundled_model, "_MODEL", None)
    monkeypatch.setitem(sys.modules, "llama_cpp", type("FakeModule", (), {"Llama": FakeLlama}))

    result = bundled_model.complete([{"role": "user", "content": "hello"}])

    assert result == {
        "content": "Ready.",
        "tool_calls": [{"id": "tool-1", "function": {
            "name": "search", "arguments": {"query": "aurora"},
        }}],
    }
    assert captured["init"]["model_path"] == str(model_file)
    assert captured["request"]["max_tokens"] == 512


def test_provider_catalog_covers_brahma_cloud_providers():
    assert set(ai_providers.OPENAI_COMPATIBLE_PROVIDERS) == {
        "Gemini",
        "OpenAI",
        "OpenRouter",
        "Groq",
        "DeepSeek",
        "Mistral",
        "Together AI",
        "Fireworks AI",
        "xAI",
        "Cerebras",
    }
    assert "Anthropic" in ai_providers.PROVIDER_NAMES
    assert ai_providers.BUNDLED_OFFLINE_PROVIDER in ai_providers.PROVIDER_NAMES


def test_cloud_provider_selection_and_model_override(monkeypatch):
    config = {
        "default_ai_provider": "OpenAI",
        "openai_api_key": "test-key",
        "cloud_models": {"OpenAI": "custom-model"},
    }
    monkeypatch.setattr(llm_client, "_load_config", lambda: config)

    assert llm_client.get_llm_provider() == "OpenAI"
    assert llm_client.get_llm_settings() == (
        ai_providers.OPENAI_COMPATIBLE_PROVIDERS["OpenAI"]["endpoint"],
        "custom-model",
    )


def test_cloud_chat_uses_selected_key_endpoint_and_model(monkeypatch):
    config = {
        "default_ai_provider": "Groq",
        "groq_api_key": "test-key",
        "cloud_models": {"Groq": "llama-test"},
    }
    monkeypatch.setattr(llm_client, "_load_config", lambda: config)
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Cloud response"}}]}

    def fake_post(endpoint, **kwargs):
        captured["endpoint"] = endpoint
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(llm_client.requests, "post", fake_post)
    result = llm_client.call_llm(
        [{"role": "user", "content": "hello"}],
        timeout=9,
    )

    assert result == {"content": "Cloud response", "tool_calls": []}
    assert captured["endpoint"] == ai_providers.OPENAI_COMPATIBLE_PROVIDERS["Groq"]["endpoint"]
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "llama-test"
    assert captured["timeout"] == 9


def test_cloud_text_call_honors_per_call_model_override(monkeypatch):
    config = {
        "default_ai_provider": "OpenAI",
        "openai_api_key": "test-key",
    }
    monkeypatch.setattr(llm_client, "_load_config", lambda: config)
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Override response"}}]}

    def fake_post(endpoint, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(llm_client.requests, "post", fake_post)
    result = llm_client.call_llm_text("hello", model="per-call-model")

    assert result == "Override response"
    assert captured["json"]["model"] == "per-call-model"


def test_anthropic_response_tool_calls_are_normalized(monkeypatch):
    config = {
        "default_ai_provider": "Anthropic",
        "anthropic_api_key": "test-key",
        "cloud_models": {"Anthropic": "claude-test"},
    }
    monkeypatch.setattr(llm_client, "_load_config", lambda: config)
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {
                "content": [
                    {"type": "text", "text": "Done."},
                    {"type": "tool_use", "id": "tool-1", "name": "search",
                     "input": {"query": "aurora"}},
                ]
            }

    def fake_post(endpoint, **kwargs):
        captured["endpoint"] = endpoint
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(llm_client.requests, "post", fake_post)
    result = llm_client.call_llm([{"role": "user", "content": "search"}], tools=[])

    assert captured["endpoint"] == ai_providers.ANTHROPIC_PROVIDER["endpoint"]
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["json"]["model"] == "claude-test"
    assert result == {
        "content": "Done.",
        "tool_calls": [{
            "id": "tool-1",
            "function": {"name": "search", "arguments": {"query": "aurora"}},
        }],
    }


def test_legacy_local_server_setting_still_routes_to_openai_compatible(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "_load_config",
        lambda: {"llm_provider": "openai", "llm_url": "http://localhost:1234", "llm_model": "local-model"},
    )
    assert llm_client.get_llm_provider() == "openai"
    assert llm_client.get_llm_settings() == ("http://localhost:1234", "local-model")


def test_bundled_offline_provider_routes_text_chat_and_stream_without_network(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "_load_config",
        lambda: {"default_ai_provider": ai_providers.BUNDLED_OFFLINE_PROVIDER},
    )
    captured = []

    def fake_complete(messages, tools=None, max_tokens=512):
        captured.append((messages, tools, max_tokens))
        return {"content": "Offline response. Ready.", "tool_calls": []}

    monkeypatch.setattr(bundled_model, "complete", fake_complete)

    assert llm_client.get_llm_provider() == ai_providers.BUNDLED_OFFLINE_PROVIDER
    assert llm_client.call_llm([{"role": "user", "content": "hello"}])["content"] == "Offline response. Ready."
    assert llm_client.call_llm_text("hello", system="Be concise") == "Offline response. Ready."
    events = list(llm_client.call_llm_stream([{"role": "user", "content": "hello"}]))
    assert [event["text"] for event in events if event["type"] == "sentence"] == [
        "Offline response.", "Ready.",
    ]
    assert events[-1] == {"type": "done", "content": "Offline response. Ready.", "tool_calls": []}
    assert [entry[2] for entry in captured] == [150, 600, 150]


def test_brahma_voice_is_fixed_and_legacy_gemini_choices_are_ignored(monkeypatch):
    monkeypatch.setattr(
        config_manager,
        "load_api_keys",
        lambda: {"voice_name": "Puck"},
    )

    assert config_manager.AVAILABLE_VOICES == ["Charon"]
    assert config_manager.get_voice() == "Charon"
    assert config_manager.BRAHMA_TTS_VOICE == "en-US-GuyNeural"
