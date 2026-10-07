import scrape


def test_normalize_url_data():
    assert scrape._normalize_url_data(None) == ("", "Untitled")
    assert scrape._normalize_url_data("not a dict") == ("", "Untitled")
    assert scrape._normalize_url_data({"link": "http://x.test/a", "title": ""}) == ("http://x.test/a", "Untitled")
    assert scrape._normalize_url_data({"link": "http://x.test/a", "title": "Real Title"}) == ("http://x.test/a", "Real Title")


def test_scrape_single_short_circuits_without_network():
    # No session/network mocking here: both guard clauses must return before
    # any connection attempt (the autouse network guard would catch a miss).
    assert scrape.scrape_single({"link": "javascript:alert(1)", "title": "XSS"}) == ("javascript:alert(1)", "XSS")
    assert scrape.scrape_single({"link": "", "title": "Nothing"}) == ("", "Nothing")


class _FakeHTTPResponse:
    def __init__(self, status_code=200, headers=None, encoding="utf-8", body=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = encoding
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size=8192):
        yield self._body

    def close(self):
        self.closed = True


class _FakeSessionScrape:
    def __init__(self, response):
        self.response = response

    def get(self, url, headers=None, timeout=None, stream=None):
        return self.response


def test_scrape_single_extracts_and_cleans_text(monkeypatch):
    body = b"<html><script>evil()</script><body>Hello   World</body></html>"
    fake_response = _FakeHTTPResponse(status_code=200, headers={"Content-Type": "text/html"}, body=body)
    monkeypatch.setattr(scrape, "_get_session", lambda use_tor=False: _FakeSessionScrape(fake_response))

    url, text = scrape.scrape_single({"link": "http://example.test/page", "title": "My Title"})

    assert url == "http://example.test/page"
    assert text == "My Title - Hello World"
    assert "evil" not in text
    assert fake_response.closed is True


def test_scrape_single_rejects_disallowed_content_type(monkeypatch):
    fake_response = _FakeHTTPResponse(status_code=200, headers={"Content-Type": "application/pdf"}, body=b"%PDF-1.4 ignored")
    monkeypatch.setattr(scrape, "_get_session", lambda use_tor=False: _FakeSessionScrape(fake_response))

    assert scrape.scrape_single({"link": "http://example.test/doc.pdf", "title": "A PDF"}) == (
        "http://example.test/doc.pdf",
        "A PDF",
    )


def test_scrape_multiple_rejects_non_list_input():
    assert scrape.scrape_multiple("not a list") == {}
    assert scrape.scrape_multiple(None) == {}


def test_scrape_multiple_dedupes_and_truncates(monkeypatch):
    long_text = "x" * (scrape.MAX_RETURN_CHARS + 500)

    def fake_scrape_single(url_data):
        if url_data["link"] == "http://a.test/":
            return url_data["link"], long_text
        return url_data["link"], "short text"

    monkeypatch.setattr(scrape, "scrape_single", fake_scrape_single)

    results = scrape.scrape_multiple(
        [
            {"link": "http://a.test/", "title": "A"},
            {"link": "http://a.test/", "title": "A dup"},
            {"link": "http://b.test/", "title": "B"},
        ]
    )

    assert set(results.keys()) == {"http://a.test/", "http://b.test/"}
    assert len(results["http://a.test/"]) == scrape.MAX_RETURN_CHARS
    assert results["http://a.test/"].endswith("...(truncated)")
    assert results["http://b.test/"] == "short text"
