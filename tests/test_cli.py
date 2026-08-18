import json

from loadweave.cli import main


def test_components_command_lists_builtins(capsys):
    assert main(["components"]) == 0
    output = capsys.readouterr().out
    assert "sources: csv, jsonl, odoo" in output
    assert "sinks: jsonl, stdout" in output


def test_check_reports_invalid_configuration(tmp_path, capsys):
    config = tmp_path / "pipeline.json"
    config.write_text("{}")
    assert main(["check", str(config)]) == 2
    assert "missing required key: source" in capsys.readouterr().err


def test_check_accepts_valid_configuration(tmp_path, capsys):
    config = tmp_path / "pipeline.json"
    config.write_text(
        json.dumps(
            {
                "source": {"use": "csv", "with": {"path": "input.csv"}},
                "sink": {"use": "stdout"},
            }
        )
    )
    assert main(["check", str(config)]) == 0
    assert f"valid: {config}" in capsys.readouterr().out


def test_run_executes_pipeline(tmp_path, capsys):
    source = tmp_path / "input.csv"
    output = tmp_path / "output.jsonl"
    config = tmp_path / "pipeline.json"
    source.write_text("name,city\nAda,London\n")
    config.write_text(
        json.dumps(
            {
                "source": {"use": "csv", "with": {"path": str(source)}},
                "transforms": [{"use": "rename", "with": {"fields": {"city": "place"}}}],
                "sink": {"use": "jsonl", "with": {"path": str(output)}},
            }
        )
    )
    assert main(["run", str(config)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["extracted"] == result["loaded"] == 1
    assert json.loads(output.read_text()) == {"name": "Ada", "place": "London"}
