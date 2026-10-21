"""comfyui-toolkit: loads every node pack in ./nodes so one clone into custom_nodes gets them all."""

import importlib
import logging
import pkgutil
from pathlib import Path

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for _pack in pkgutil.iter_modules([str(Path(__file__).parent / "nodes")]):
    try:
        _module = importlib.import_module(f".nodes.{_pack.name}", __name__)
    except Exception:
        logging.exception("comfyui-toolkit: failed to load node pack '%s'", _pack.name)
        continue
    NODE_CLASS_MAPPINGS.update(getattr(_module, "NODE_CLASS_MAPPINGS", {}))
    NODE_DISPLAY_NAME_MAPPINGS.update(getattr(_module, "NODE_DISPLAY_NAME_MAPPINGS", {}))

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
