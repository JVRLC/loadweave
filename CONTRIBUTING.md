# Contributing

Thank you for improving LoadWeave. Search existing issues first and open an issue before a
large change. Small fixes may go directly to a pull request. Keep components focused, add
tests for new behavior, and update the changelog for changes visible to users.

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

Contributions are licensed under the MIT License.

## Commit and review style

Use concise imperative commits, preferably Conventional Commits such as `feat:`, `fix:`,
`docs:`, or `build(deps):`. Pull requests are squash-merged after review. Be kind and follow
the [Code of Conduct](CODE_OF_CONDUCT.md).
