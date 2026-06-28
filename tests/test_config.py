""" test runtime config helpers """

from whisperflow import config


def test_get_int_default(monkeypatch):
    """missing env falls back to default"""
    monkeypatch.delenv("WF_TEST_INT", raising=False)
    assert config.get_int("WF_TEST_INT", 7) == 7


def test_get_int_valid(monkeypatch):
    """valid env is parsed"""
    monkeypatch.setenv("WF_TEST_INT", "42")
    assert config.get_int("WF_TEST_INT", 7) == 42


def test_get_int_invalid(monkeypatch):
    """invalid env falls back to default"""
    monkeypatch.setenv("WF_TEST_INT", "not-int")
    assert config.get_int("WF_TEST_INT", 7) == 7


def test_get_float_valid(monkeypatch):
    """valid float env is parsed"""
    monkeypatch.setenv("WF_TEST_FLOAT", "2.5")
    assert config.get_float("WF_TEST_FLOAT", 1.5) == 2.5


def test_get_float_invalid(monkeypatch):
    """invalid float env falls back to default"""
    monkeypatch.setenv("WF_TEST_FLOAT", "x")
    assert config.get_float("WF_TEST_FLOAT", 1.5) == 1.5
