import socket
import sys
from types import ModuleType

import pytest


@pytest.fixture(autouse=True)
def _bez_site(monkeypatch):
    def zakazano(*args, **kwargs):
        raise RuntimeError("testy nesmí na síť")
    monkeypatch.setattr(socket.socket, "connect", zakazano)


# requirements.txt pulls streamlit + the full langchain stack (unpinned) just so
# llm_utils.py can reference Chat* classes as dict values. We only test pure
# selection/gating logic, never instantiate a real LLM, so stub the imports
# instead of installing gigabytes of unrelated packages in CI.
# ponytail: minimal class-identity stubs, not real langchain behavior — swap
# for real installs if a test ever needs actual langchain behavior.
def _stub(name, **attrs):
    mod = ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)


class _FakeChatOpenAI:
    def __init__(self, *a, **k):
        pass


class _FakeChatOllama:
    def __init__(self, *a, **k):
        pass


class _FakeChatAnthropic:
    def __init__(self, *a, **k):
        pass


class _FakeChatGoogleGenerativeAI:
    def __init__(self, *a, **k):
        pass


_stub("langchain_openai", ChatOpenAI=_FakeChatOpenAI)
_stub("langchain_ollama", ChatOllama=_FakeChatOllama)
_stub("langchain_anthropic", ChatAnthropic=_FakeChatAnthropic)
_stub("langchain_google_genai", ChatGoogleGenerativeAI=_FakeChatGoogleGenerativeAI)
_stub("langchain_core")
_stub("langchain_core.callbacks")
_stub("langchain_core.callbacks.base", BaseCallbackHandler=object)
