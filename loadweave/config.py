from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any

_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

class ConfigError(ValueError):
    pass

def _expand(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in os.environ:
                raise ConfigError(f"environment variable {name!r} is not set")
            return os.environ[name]
        return _ENV.sub(replace, value)
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value

def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load {config_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError("pipeline configuration must be a JSON object")
    for required in ("source", "sink"):
        if required not in value:
            raise ConfigError(f"missing required key: {required}")
    if not isinstance(value.get("transforms", []), list):
        raise ConfigError("transforms must be a list")
    return _expand(value)

