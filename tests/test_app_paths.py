import os

from src.logic import app_paths


def test_source_runtime_root_is_project_build(monkeypatch):
    monkeypatch.delattr(app_paths.sys, "frozen", raising=False)

    expected = os.path.abspath(os.path.join(os.path.dirname(app_paths.__file__), "..", "..", "build"))

    assert app_paths.get_runtime_root() == expected
    assert app_paths.get_app_state_path() == os.path.join(expected, "app_state.json")


def test_frozen_runtime_root_is_executable_directory(monkeypatch, tmp_path):
    executable = tmp_path / "TestAuto.exe"
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str(executable))

    assert app_paths.get_runtime_root() == str(tmp_path)
    assert app_paths.get_app_state_path() == str(tmp_path / "app_state.json")
