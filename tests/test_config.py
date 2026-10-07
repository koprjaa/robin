import config


def test_clean_env(monkeypatch):
    monkeypatch.setenv("ROBIN_TEST_VAR", '"quoted value"')
    assert config._clean_env("ROBIN_TEST_VAR") == "quoted value"

    monkeypatch.setenv("ROBIN_TEST_VAR2", "'single quoted'")
    assert config._clean_env("ROBIN_TEST_VAR2") == "single quoted"

    monkeypatch.delenv("ROBIN_TEST_MISSING", raising=False)
    assert config._clean_env("ROBIN_TEST_MISSING", "fallback") == "fallback"
    assert config._clean_env("ROBIN_TEST_MISSING") is None
