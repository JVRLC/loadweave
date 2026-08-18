from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, cast

_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ConfigError(ValueError):
    pass


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConfigError(f"cannot load {env_path}: {exc}") from exc

    for number, original in enumerate(lines, 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not _ENV_NAME.fullmatch(name):
            raise ConfigError(f"{env_path}:{number}: invalid environment assignment")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(name, value)


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
    expanded = _expand(value)
    for key in ("source", "sink"):
        if not isinstance(expanded[key], dict):
            raise ConfigError(f"{key} must be an object")
    if not all(isinstance(item, dict) for item in expanded.get("transforms", [])):
        raise ConfigError("every transform must be an object")
    return cast(dict[str, Any], expanded)
