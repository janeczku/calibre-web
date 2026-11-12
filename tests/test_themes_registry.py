from cps import themes


def test_legacy_theme_identifier():
    assert themes.legacy_theme_identifier(0) == "standard"
    assert themes.legacy_theme_identifier(1) == "caliblur"
    assert themes.legacy_theme_identifier(2) == "standard"
    assert themes.legacy_theme_identifier(None) == "standard"
    assert themes.legacy_theme_identifier("x") == "standard"


def test_available_themes_come_from_info_json(theme_app):
    with theme_app.app_context():
        assert [t.identifier for t in themes.get_available_themes()] == ["caliblur", "standard"]


def test_get_theme_unknown_falls_back(theme_app):
    with theme_app.app_context():
        assert themes.get_theme("gone").identifier == "standard"
        assert themes.get_theme(None).identifier == "standard"
        assert not themes.is_valid_theme("gone")
        assert themes.is_valid_theme("caliblur")


def test_basic_blueprint_uses_standard(theme_app):
    with theme_app.app_context():
        assert themes.get_theme_identifier("caliblur", "basic") == "standard"
        assert themes.get_theme_identifier("caliblur", "web") == "caliblur"
