# LoadWeave

**Build readable ETL pipelines from tiny, reusable pieces.**

LoadWeave is a dependency-free Python runner for lightweight data jobs. Describe a pipeline
in JSON, run it locally or in a container, and extend it with ordinary Python classes.

```text
CSV / plugin source  ->  select  ->  rename  ->  JSONL / plugin sink
```

## Why LoadWeave?

- **Small core** — no scheduler, server, or framework lock-in.
- **Streaming** — records flow one at a time instead of filling memory.
- **Composable** — sources, transforms, and sinks use three minimal interfaces.
- **Portable** — environment-aware configuration runs anywhere Python runs.
- **Extensible** — use `package.module:Class` to load your own component.

## Quick start

```bash
python -m pip install loadweave
loadweave run examples/csv-to-jsonl/pipeline.json
```

```json
{
  "source": {"use": "csv", "with": {"path": "examples/csv-to-jsonl/people.csv"}},
  "transforms": [
    {"use": "select", "with": {"fields": ["name", "city"]}},
    {"use": "rename", "with": {"fields": {"city": "location"}}}
  ],
  "sink": {"use": "jsonl", "with": {"path": "build/people.jsonl"}}
}
```

```bash
loadweave components
loadweave check path/to/pipeline.json
loadweave run path/to/pipeline.json
```

## Write a plugin

```python
class AddSource:
    def __init__(self, start=0, stop=10):
        self.start, self.stop = start, stop

    def read(self):
        for value in range(self.start, self.stop):
            yield {"value": value}
```

Reference it as `my_package.sources:AddSource`. A transform implements `apply(record)` and
returns a record or `None`; a sink implements `write(records)` and returns the count written.

Any string can contain `${ENVIRONMENT_VARIABLE}`. Missing variables fail early. Keep secrets
outside configuration files and never commit `.env` files.

Plugin references import and execute Python code. Only run pipeline configurations and plugins
from sources you trust.

## Community

Read the [roadmap](ROADMAP.md), propose ideas in GitHub Discussions, and check the
[contribution guide](CONTRIBUTING.md) before opening a pull request. Project decisions follow
the public [governance model](GOVERNANCE.md) and community interactions follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

Releases follow Semantic Versioning and are documented in the [changelog](CHANGELOG.md).
Licensed under the [MIT License](LICENSE).
