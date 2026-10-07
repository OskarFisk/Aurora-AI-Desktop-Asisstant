"""Cloud-model provider metadata and settings for A.U.R.O.R.A."""
from __future__ import annotations

import json
from typing import Any

from memory.config_manager import CONFIG_FILE, ensure_config_dir


OPENAI_COMPATIBLE_PROVIDERS = {
    "Gemini": {
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash",
        "key_field": "gemini_api_key",
    },
    "OpenAI": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "key_field": "openai_api_key",
    },
    "OpenRouter": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-4o-mini",
        "key_field": "openrouter_api_key",
    },
    "Groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "key_field": "groq_api_key",
    },
    "DeepSeek": {
        "endpoint": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "key_field": "deepseek_api_key",
    },
    "Mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-small-latest",
        "key_field": "mistral_api_key",
    },
    "Together AI": {
        "endpoint": "https://api.together.xyz/v1/chat/completions",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "key_field": "together_api_key",
    },
    "Fireworks AI": {
        "endpoint": "https://api.fireworks.ai/inference/v1/chat/completions",
        "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "key_field": "fireworks_api_key",
    },
    "xAI": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3-mini",
        "key_field": "xai_api_key",
    },
    "Cerebras": {
        "endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "model": "llama-3.3-70b",
        "key_field": "cerebras_api_key",
    },
}

ANTHROPIC_PROVIDER = {
    "endpoint": "https://api.anthropic.com/v1/messages",
    "model": "claude-sonnet-4-20250514",
    "key_field": "anthropic_api_key",
}

PROVIDER_NAMES = ("Ollama", "Local Server", *OPENAI_COMPATIBLE_PROVIDERS, "Anthropic")


def load_api_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_provider_settings(
    provider: str,
    api_keys: dict[str, str],
    models: dict[str, str],
    local_url: str = "",
    local_model: str = "",
) -> None:
    """Persist provider choices while retaining all unrelated app settings."""
    if provider not in PROVIDER_NAMES:
        raise ValueError(f"Unsupported AI provider: {provider}")

    ensure_config_dir()
    data = load_api_config()
    data["default_ai_provider"] = provider
    if provider == "Ollama":
        data["llm_provider"] = "ollama"
    elif provider == "Local Server":
        data["llm_provider"] = "openai"
    if local_url.strip():
        data["llm_url"] = local_url.strip().rstrip("/")
    if local_model.strip():
        data["llm_model"] = local_model.strip()
    cloud_models = data.get("cloud_models")
    if not isinstance(cloud_models, dict):
        cloud_models = {}
    for name, config in OPENAI_COMPATIBLE_PROVIDERS.items():
        model = str(models.get(name, "")).strip()
        if model:
            cloud_models[name] = model
        key = str(api_keys.get(name, "")).strip()
        if key:
            data[config["key_field"]] = key

    model = str(models.get("Anthropic", "")).strip()
    if model:
        cloud_models["Anthropic"] = model
    key = str(api_keys.get("Anthropic", "")).strip()
    if key:
        data[ANTHROPIC_PROVIDER["key_field"]] = key

    data["cloud_models"] = cloud_models
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_provider_config(provider: str) -> dict[str, str] | None:
    if provider == "Anthropic":
        return ANTHROPIC_PROVIDER
    return OPENAI_COMPATIBLE_PROVIDERS.get(provider)
