from pathlib import Path

import tgaggerator.cli as cli


def test_build_stack_specs_without_bot():
    specs = cli._build_stack_specs(
        interval=15,
        api_port=8010,
        ui_port=8600,
        collector=True,
        api=True,
        ui=True,
        with_bot=False,
    )
    names = [s["name"] for s in specs]

    assert names == ["collector", "api", "ui"]
    assert specs[0]["cmd"][-1] == "15"
    assert specs[2]["cmd"][-1] == "8600"
    assert specs[1]["env"]["API_PORT"] == "8010"
    assert specs[2]["env"]["UI_API_BASE"] == "http://127.0.0.1:8010"


def test_build_stack_specs_with_bot():
    specs = cli._build_stack_specs(
        interval=30,
        api_port=8000,
        ui_port=8502,
        collector=True,
        api=True,
        ui=True,
        with_bot=True,
    )
    names = [s["name"] for s in specs]
    assert names == ["collector", "api", "ui", "telegram-ui"]


def test_build_stack_specs_selected_components_only():
    specs = cli._build_stack_specs(
        interval=30,
        api_port=8000,
        ui_port=8502,
        collector=False,
        api=True,
        ui=False,
        with_bot=False,
    )
    assert [s["name"] for s in specs] == ["api"]


def test_stack_state_roundtrip(tmp_path: Path, monkeypatch):
    state_file = tmp_path / "runtime" / "stack.json"
    monkeypatch.setattr(cli, "STACK_PID_FILE", state_file)

    specs = [
        {"name": "api", "pid": 111, "cmd": ["python", "scripts/run_api.py"]},
        {"name": "ui", "pid": 222, "cmd": ["python", "-m", "streamlit"]},
    ]
    cli._write_stack_state(specs)
    state = cli._read_stack_state()

    assert state is not None
    assert state["processes"][0]["pid"] == 111
    assert state["processes"][1]["name"] == "ui"

    cli._clear_stack_state()
    assert not state_file.exists()


def test_pid_alive_windows_parsing(monkeypatch):
    class _Proc:
        def __init__(self, stdout: str):
            self.stdout = stdout

    monkeypatch.setattr(cli, "os", type("OS", (), {"name": "nt", "kill": staticmethod(lambda *_: None)}))

    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: _Proc('"python.exe","1234","Console","1","10,000 K"\n'),
    )
    assert cli._pid_alive(1234) is True

    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: _Proc("INFO: No tasks are running which match the specified criteria.\n"),
    )
    assert cli._pid_alive(1234) is False
