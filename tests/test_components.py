import json
from io import StringIO

import pytest

from loadweave.components import (
    DropEmpty,
    JsonlSink,
    JsonlSource,
    RenameFields,
    SelectFields,
    StdoutSink,
)


def test_transforms_are_composable():
    record = {"name": "Ada", "city": "London", "unused": 1}
    selected = SelectFields(["name", "city"]).apply(record)
    assert RenameFields({"city": "location"}).apply(selected) == {
        "name": "Ada",
        "location": "London",
    }


def test_drop_empty_filters_blank_values():
    transform = DropEmpty("name")
    assert transform.apply({"name": ""}) is None
    assert transform.apply({"name": "Ada"}) == {"name": "Ada"}


def test_jsonl_source_rejects_non_object(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_text("[1, 2, 3]\n")
    with pytest.raises(ValueError, match="expected a JSON object"):
        list(JsonlSource(str(source)).read())


def test_jsonl_source_ignores_blank_lines(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_text('\n{"name": "Ada"}\n\n')
    assert list(JsonlSource(str(source)).read()) == [{"name": "Ada"}]


def test_stdout_sink_writes_records():
    stream = StringIO()
    assert StdoutSink(stream).write([{"name": "Ada"}]) == 1
    assert json.loads(stream.getvalue()) == {"name": "Ada"}


def test_jsonl_sink_replaces_output_atomically(tmp_path):
    output = tmp_path / "output.jsonl"
    output.write_text("old content\n")
    JsonlSink(str(output)).write([{"name": "Ada"}])
    assert json.loads(output.read_text()) == {"name": "Ada"}


def test_jsonl_sink_preserves_previous_output_on_failure(tmp_path):
    output = tmp_path / "output.jsonl"
    output.write_text("old content\n")

    def broken_records():
        yield {"name": "Ada"}
        raise RuntimeError("source failed")

    with pytest.raises(RuntimeError, match="source failed"):
        JsonlSink(str(output)).write(broken_records())
    assert output.read_text() == "old content\n"
    assert list(tmp_path.glob(".output.jsonl.*")) == []
