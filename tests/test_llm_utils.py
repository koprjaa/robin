import llm_utils


def _no_dynamic_models(monkeypatch):
    """Block the three real-HTTP model-discovery calls regardless of ambient env."""
    monkeypatch.setattr(llm_utils, "fetch_ollama_models", lambda: [])
    monkeypatch.setattr(llm_utils, "fetch_llama_cpp_models", lambda: [])
    monkeypatch.setattr(llm_utils, "fetch_custom_api_models", lambda: [])
    monkeypatch.setattr(llm_utils.config, "CUSTOM_API_MODEL", None)


def test_is_set_and_normalize_model_name():
    assert llm_utils._is_set(None) is False
    assert llm_utils._is_set("") is False
    assert llm_utils._is_set("   ") is False
    assert llm_utils._is_set("your_api_key_here") is False
    assert llm_utils._is_set("sk-real-123") is True
    assert llm_utils._normalize_model_name("  GPT-4.1  ") == "gpt-4.1"


def test_get_model_choices_gates_by_available_api_keys(monkeypatch):
    _no_dynamic_models(monkeypatch)
    monkeypatch.setattr(llm_utils, "OPENAI_API_KEY", "sk-real")
    monkeypatch.setattr(llm_utils, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(llm_utils, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(llm_utils, "OPENROUTER_API_KEY", None)

    choices = llm_utils.get_model_choices()

    assert "gpt-4.1" in choices
    assert "claude-sonnet-4-5" not in choices
    assert "gemini-2.5-flash" not in choices
    assert not any("openrouter" in c for c in choices)


def test_resolve_model_config(monkeypatch):
    _no_dynamic_models(monkeypatch)

    known = llm_utils.resolve_model_config("GPT-4.1")  # case-insensitive
    assert known["class"] is llm_utils.ChatOpenAI  # stubbed class from conftest
    assert known["constructor_params"]["model_name"] == "gpt-4.1"

    assert llm_utils.resolve_model_config("not-a-real-model") is None


def test_buffered_streaming_handler_flushes_on_newline_and_limit():
    seen = []
    handler = llm_utils.BufferedStreamingHandler(buffer_limit=10, ui_callback=seen.append)

    handler.on_llm_new_token("hello\n")
    assert seen == ["hello\n"]
    assert handler.buffer == ""

    handler.on_llm_new_token("0123456789")  # hits buffer_limit exactly
    assert seen == ["hello\n", "0123456789"]

    handler.on_llm_new_token("tail")
    assert seen == ["hello\n", "0123456789"]  # below limit, not flushed yet

    handler.on_llm_end(response=None)
    assert seen[-1] == "tail"
