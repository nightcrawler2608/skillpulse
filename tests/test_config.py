from skillpulse import config


def test_roles_and_cities_are_unique():
    assert len({r.name for r in config.ROLES}) == len(config.ROLES)
    assert len({c.name for c in config.CITIES}) == len(config.CITIES)


def test_daily_calls_within_free_quota():
    # The daily run must stay under our safety cap (which is under Adzuna's limit).
    assert config.planned_daily_calls() <= config.ADZUNA_MAX_CALLS_PER_DAY


def test_every_role_has_keywords():
    for role in config.ROLES:
        assert role.search_term
        assert role.title_keywords


def test_missing_setting_raises_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = config.Settings.from_env()
    try:
        settings.require("database_url")
    except config.MissingSettingError as e:
        assert "DATABASE_URL" in str(e)
    else:
        raise AssertionError("expected MissingSettingError")


def test_app_db_url_swaps_only_the_user_and_password():
    from skillpulse.db.app_role import app_url
    url = app_url("postgresql://owner:secret@ep-x.aws.neon.tech/neondb?sslmode=require", "p/w+1")
    assert url == "postgresql://skillpulse_app:p%2Fw%2B1@ep-x.aws.neon.tech/neondb?sslmode=require"


def test_wilson_interval_is_honest_for_small_samples():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "usage_report", Path(__file__).parents[1] / "scripts" / "usage_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lo, hi = mod.wilson(4, 5)          # 80% from only 5 votes: wide interval
    assert lo < 0.4 and hi > 0.95
    lo, hi = mod.wilson(400, 500)      # same 80% from 500 votes: narrow
    assert 0.76 < lo < 0.80 < hi < 0.84
    assert mod.wilson(0, 0) == (0.0, 0.0)
