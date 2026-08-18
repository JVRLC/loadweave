from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from loadweave.components import (
    CsvSource,
    DropEmpty,
    JsonlSink,
    JsonlSource,
    OdooSource,
    RenameFields,
    SelectFields,
    StdoutSink,
)
from loadweave.contracts import Sink, Source, Transform

SOURCES = {"csv": CsvSource, "jsonl": JsonlSource, "odoo": OdooSource}
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
    return cast(type[Any], component)


def build(spec: dict[str, Any], registry: dict[str, type[Any]]) -> Any:
    if not isinstance(spec, dict) or not isinstance(spec.get("use"), str):
        raise ValueError("component requires a string 'use' field")
    options = spec.get("with", {})
    if not isinstance(options, dict):
        raise ValueError("component 'with' field must be an object")
    return resolve(spec["use"], registry)(**options)


def build_source(spec: dict[str, Any]) -> Source:
    component = build(spec, SOURCES)
    if not isinstance(component, Source):
        raise TypeError(f"source {spec.get('use')!r} must implement read()")
    return component


def build_transform(spec: dict[str, Any]) -> Transform:
    component = build(spec, TRANSFORMS)
    if not isinstance(component, Transform):
        raise TypeError(f"transform {spec.get('use')!r} must implement apply()")
    return component


def build_sink(spec: dict[str, Any]) -> Sink:
    component = build(spec, SINKS)
    if not isinstance(component, Sink):
        raise TypeError(f"sink {spec.get('use')!r} must implement write()")
    return component
