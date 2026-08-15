import json

import pytest

from loadweave.config import ConfigError, load_config


def test_expands_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_PATH", "build/data.jsonl")
    path = tmp_path / "pipeline.json"
    path.write_text(
        json.dumps(
            {
                "source": {"use": "csv", "with": {"path": "input.csv"}},
                "sink": {"use": "jsonl", "with": {"path": "${OUTPUT_PATH}"}},
            }
        )
    )
    assert load_config(path)["sink"]["with"]["path"] == "build/data.jsonl"


def test_missing_environment_variable_is_clear(tmp_path):
    path = tmp_path / "pipeline.json"
    path.write_text(
        json.dumps(
            {
                "source": {"use": "csv", "with": {"path": "${MISSING_INPUT}"}},
                "sink": {"use": "stdout"},
            }
        )
    )
    with pytest.raises(ConfigError, match="MISSING_INPUT"):
        load_config(path)


def test_wraps_invalid_json_with_path(tmp_path):
    path = tmp_path / "pipeline.json"
    path.write_text("not json")
    with pytest.raises(ConfigError, match=r"cannot load .*pipeline\.json"):
        load_config(path)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"sink": {"use": "stdout"}}, "missing required key: source"),
        (["not", "an", "object"], "pipeline configuration must be a JSON object"),
        ({"source": [], "sink": {"use": "stdout"}}, "source must be an object"),
        (
            {"source": {"use": "csv"}, "transforms": {}, "sink": {"use": "stdout"}},
            "transforms must be a list",
        ),
        (
            {"source": {"use": "csv"}, "transforms": ["bad"], "sink": {"use": "stdout"}},
            "every transform must be an object",
        ),
    ],
)
def test_rejects_invalid_structure(tmp_path, config, message):
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ConfigError, match=message):
        load_config(path)
