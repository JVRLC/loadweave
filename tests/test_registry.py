import pytest

from loadweave.registry import build_sink, build_source, resolve


def test_unknown_component_lists_choices():
    with pytest.raises(ValueError, match="built-ins: csv, jsonl"):
        build_source({"use": "missing"})


def test_source_contract_is_validated():
    with pytest.raises(TypeError, match=r"must implement read\(\)"):
        build_source({"use": "tests.test_registry:NotASource"})


def test_sink_contract_is_validated():
    with pytest.raises(TypeError, match=r"must implement write\(\)"):
        build_sink({"use": "tests.test_registry:NotASource"})


def test_non_callable_plugin_is_rejected():
    with pytest.raises(TypeError, match="not callable"):
        resolve("tests.test_registry:NOT_CALLABLE", {})


class NotASource:
    pass


NOT_CALLABLE = 42
