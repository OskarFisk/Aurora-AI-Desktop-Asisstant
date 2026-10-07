"""Lazy CPU inference for the optional bundled Qwen text model."""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

MODEL_FILENAME = "Qwen_Qwen3-0.6B-Q6_K.gguf"
_MODEL = None
_MODEL_LOCK = threading.Lock()


def model_path() -> Path:
    """Locate the model in a PyInstaller bundle or source checkout."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / "assets" / "models" / MODEL_FILENAME


def is_available() -> bool:
    return model_path().is_file()


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    path = model_path()
    if not path.is_file():
        raise RuntimeError(
            "The bundled offline model is only included in the Windows release."
        )
    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("The offline model runtime is not available in this install.") from exc
    _MODEL = Llama(
        model_path=str(path),
        n_ctx=4096,
        n_threads=min(8, max(1, os.cpu_count() or 2)),
        verbose=False,
    )
    return _MODEL


def complete(messages: list[dict], tools: list | None = None, max_tokens: int = 512) -> dict:
    """Generate a chat completion and normalize it to A.U.R.O.R.A's LLM shape."""
    with _MODEL_LOCK:
        response = _load_model().create_chat_completion(
            messages=messages,
            tools=tools or None,
            max_tokens=max_tokens,
            temperature=0.3,
        )

    try:
        message = response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("The offline model returned an invalid chat response.") from exc

    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                pass
        tool_calls.append({
            "id": call.get("id", ""),
            "function": {
                "name": function.get("name", ""),
                "arguments": arguments,
            },
        })
    return {
        "content": str(message.get("content") or "").strip(),
        "tool_calls": tool_calls,
    }