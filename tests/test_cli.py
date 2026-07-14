from __future__ import annotations

from pathlib import Path

import pytest

from investment_os.app.cli import main


@pytest.fixture()
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVOS_DATABASE_PATH", str(tmp_path / "cli.db"))
    monkeypatch.setenv("INVOS_LLM_PROVIDER", "off")


def test_health_ok(cli_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["health"]) == 0
    assert "ok" in capsys.readouterr().out


def test_health_reports_broken_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("INVOS_DATABASE_PATH", "/proc/nonexistent/x.db")
    monkeypatch.setenv("INVOS_LLM_PROVIDER", "off")
    assert main(["health"]) == 1
    assert "unhealthy" in capsys.readouterr().err


def test_eval_command_exit_codes(
    cli_env: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["eval"]) == 0
    assert "4/4" in capsys.readouterr().out

    broken = tmp_path / "broken.json"
    broken.write_text(
        """
        {
          "fixture": "data/fixtures/idx_demo.json",
          "cases": [
            {"name": "salah", "ticker": "BBCA", "rationale": "regresi disengaja",
             "expect": {"verdict": "SELL"}}
          ]
        }
        """
    )
    assert main(["eval", "--suite", str(broken)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_analyze_and_history_roundtrip(cli_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["analyze", "ANTM"]) == 0
    out = capsys.readouterr().out
    assert "HOLD" in out and "R1" in out

    assert main(["history"]) == 0
    assert "ANTM HOLD" in capsys.readouterr().out


def test_analyze_unknown_ticker_fails(cli_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["analyze", "ZZZZ"]) == 1
    assert "error" in capsys.readouterr().err
