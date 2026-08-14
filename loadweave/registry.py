from __future__ import annotations
from importlib import import_module
from typing import Any
from loadweave.components import CsvSource, DropEmpty, JsonlSink, JsonlSource, RenameFields, SelectFields, StdoutSink

SOURCES = {"csv": CsvSource, "jsonl": JsonlSource}
TRANSFORMS = {"select": SelectFields, "rename": RenameFields, "drop-empty": DropEmpty}
SINKS = {"jsonl": JsonlSink, "stdout": StdoutSink}

def resolve(name: str, registry: dict[str, type[Any]]) -> type[Any]:
    if name in registry:
        return registry[name]
    if ":" not in name:
        raise ValueError(f"unknown component {name!r}; built-ins: {', '.join(sorted(registry))}")
    module_name, attribute = name.split(":", 1)
    component = getattr(import_module(module_name), attribute)
    if not callable(component):
        raise TypeError(f"plugin {name!r} is not callable")
    return component

def build(spec: dict[str, Any], registry: dict[str, type[Any]]) -> Any:
    if not isinstance(spec, dict) or not isinstance(spec.get("use"), str):
        raise ValueError("component requires a string 'use' field")
    options = spec.get("with", {})
    if not isinstance(options, dict):
        raise ValueError("component 'with' field must be an object")
    return resolve(spec["use"], registry)(**options)

