from __future__ import annotations

import importlib
import importlib.util


def test_import_grammatic() -> None:
    spec = importlib.util.find_spec("grammatic")
    assert spec is not None, "Install project into venv (`pip install -e .`) or configure src path"

    module = importlib.import_module("grammatic")
    assert module.__name__ == "grammatic"
