from focusgroup.config import DEFAULT_BASE_URL, DEFAULT_MODEL, Settings


def test_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = Settings.load(env={})
    assert s.base_url == DEFAULT_BASE_URL
    assert s.models == [DEFAULT_MODEL]
    assert s.api_key is None
    assert s.report_model == DEFAULT_MODEL


def test_ini_then_env_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "focusgroup.ini").write_text(
        "[provider]\n"
        "base_url = http://localhost:11434/v1\n"
        'models = "a/one, b/two"\n'
        "analyst_model = c/three\n"
        "api_key_env = MY_KEY\n"
        "concurrency = 3\n"
    )
    s = Settings.load(env={"MY_KEY": "k1"})
    assert s.base_url == "http://localhost:11434/v1"
    assert s.models == ["a/one", "b/two"]
    assert s.report_model == "c/three"
    assert s.api_key == "k1"
    assert s.concurrency == 3

    s = Settings.load(env={"FOCUSGROUP_MODELS": "x/y", "OPENROUTER_API_KEY": "k2"})
    assert s.models == ["x/y"]
    assert s.api_key == "k2"


def test_key_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = Settings.load(env={"OPENAI_API_KEY": "openai", "FOCUSGROUP_API_KEY": "fg"})
    assert s.api_key == "fg"
