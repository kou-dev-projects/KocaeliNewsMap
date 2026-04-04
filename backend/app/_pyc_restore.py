from __future__ import annotations

from importlib.machinery import SourcelessFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from typing import Any


_BACKUP_ROOT = Path(__file__).resolve().parents[1] / "_codex_restore_pyc"


def load_module_from_pyc(
    module_name: str,
    backup_filename: str,
    target_globals: dict[str, Any],
) -> ModuleType:
    pyc_path = _BACKUP_ROOT / backup_filename
    if not pyc_path.exists():
        raise FileNotFoundError(f"Restore pyc not found: {pyc_path}")

    is_package = "__init__." in backup_filename
    loader = SourcelessFileLoader(module_name, str(pyc_path))
    spec = spec_from_loader(
        module_name,
        loader,
        origin=str(pyc_path),
        is_package=is_package,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create restore spec for {module_name}")
    if is_package:
        spec.submodule_search_locations = [str(pyc_path.parent)]

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    target_globals.update(module.__dict__)
    return module
