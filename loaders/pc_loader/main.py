"""Entry point for pc_loader. Set PC_PROVIDER to select a loader."""

import importlib
import logging
import os

from loaders.pc_loader.runner import run

logger = logging.getLogger(__name__)

PROVIDERS = {
    "aurea":  "loaders.pc_loader.providers.aurea.AureaLoader",
    "bdd_pc": "loaders.pc_loader.providers.bdd_pc.BddPCLoader",
    "esdac":  "loaders.pc_loader.providers.esdac.EsdacLoader",
}


def _load_class(dotted_path: str):
    """Import and return a class from a dotted path string."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    provider = os.getenv("PC_PROVIDER", "").strip().lower()
    if provider not in PROVIDERS:
        raise SystemExit(
            f"PC_PROVIDER='{provider}' unknown. Accepted values: {list(PROVIDERS)}"
        )

    logger.info("Starting pc_loader with provider: %s", provider)
    loader_class = _load_class(PROVIDERS[provider])
    run(loader_class())


if __name__ == "__main__":
    main()
