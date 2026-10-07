from pathlib import Path

import search

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "sample_search_results.html").read_text()


class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class _FakeSession:
    """Records every requested URL instead of hitting the network."""

    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.requested_urls = []

    def get(self, url, headers=None, timeout=None):
        self.requested_urls.append(url)
        if self.exc:
            raise self.exc
        return self.response


def test_fetch_search_results_parses_and_filters_onion_links(monkeypatch):
    fake_session = _FakeSession(response=_FakeResponse(200, FIXTURE_HTML))
    monkeypatch.setattr(search, "get_tor_session", lambda: fake_session)

    results = search.fetch_search_results("http://example.onion/search?q={query}", "my query")

    assert results == [
        {"title": "A Real Result Page", "link": "http://exampleoniontarget1234567890abcdefghijklmno.onion/page1"},
        {"title": "Second Valid Onion Result", "link": "http://anotheronion0987654321zyxwvutsrqponmlkjih.onion/thread/42"},
    ]
    # endpoint.format(query=...) must have actually substituted the query
    assert fake_session.requested_urls == ["http://example.onion/search?q=my query"]


def test_fetch_search_results_returns_empty_list_on_non_200(monkeypatch):
    fake_session = _FakeSession(response=_FakeResponse(503, "service unavailable"))
    monkeypatch.setattr(search, "get_tor_session", lambda: fake_session)

    assert search.fetch_search_results("http://example.onion/search?q={query}", "q") == []


def test_fetch_search_results_returns_empty_list_on_exception(monkeypatch):
    fake_session = _FakeSession(exc=ConnectionError("tor down"))
    monkeypatch.setattr(search, "get_tor_session", lambda: fake_session)

    assert search.fetch_search_results("http://example.onion/search?q={query}", "q") == []


def test_get_search_results_deduplicates_by_trailing_slash(monkeypatch):
    def fake_fetch(endpoint, query):
        if "engine-a" in endpoint:
            return [{"title": "Dup result", "link": "http://dup.onion/page/"}]
        if "engine-b" in endpoint:
            return [{"title": "Dup result again", "link": "http://dup.onion/page"}]
        return [{"title": "Unique result", "link": "http://unique.onion/x"}]

    monkeypatch.setattr(search, "fetch_search_results", fake_fetch)
    monkeypatch.setattr(
        search,
        "DEFAULT_SEARCH_ENGINES",
        ["http://engine-a.onion/search?q={query}", "http://engine-b.onion/search?q={query}", "http://engine-c.onion/search?q={query}"],
    )

    # max_workers=1 forces sequential (deterministic) completion order,
    # matching DEFAULT_SEARCH_ENGINES order, so the dedup winner is stable.
    results = search.get_search_results("q", max_workers=1)

    links = sorted(r["link"] for r in results)
    assert links == ["http://dup.onion/page/", "http://unique.onion/x"]
