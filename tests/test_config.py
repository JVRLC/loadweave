import json
import pytest
from loadweave.config import ConfigError, load_config

def test_expands_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_PATH", "build/data.jsonl")
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps({"source": {"use": "csv", "with": {"path": "input.csv"}}, "sink": {"use": "jsonl", "with": {"path": "${OUTPUT_PATH}"}}}))
    assert load_config(path)["sink"]["with"]["path"] == "build/data.jsonl"

def test_missing_environment_variable_is_clear(tmp_path):
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps({"source": {"use": "csv", "with": {"path": "${MISSING_INPUT}"}}, "sink": {"use": "stdout"}}))
    with pytest.raises(ConfigError, match="MISSING_INPUT"):
        load_config(path)

