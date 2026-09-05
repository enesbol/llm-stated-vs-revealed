"""Load envs/funding_email/vendor/model_forensics_paper/api.py as a module.

Vendored upstream code (see PROVENANCE.md) is deliberately NOT part of the
installable package -- importing it via importlib keeps that boundary
explicit instead of quietly copying it into src/ or adding vendor/ to
sys.path as if it were ours. Only funding_email's env needs this: it is the
only env with a real anchor-file vendor dependency on the paper's own
OpenRouter client wrapper. Eval Tampering's live calls reuse the same client
(the wrapper is generic), so this loader is shared, not funding_email-only.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
_VENDOR_API_PATH = REPO_ROOT / "envs" / "funding_email" / "vendor" / "model_forensics_paper" / "api.py"

_cached: ModuleType | None = None


def load() -> ModuleType:
    global _cached
    if _cached is not None:
        return _cached
    if not _VENDOR_API_PATH.exists():
        raise FileNotFoundError(f"{_VENDOR_API_PATH} missing.")
    spec = importlib.util.spec_from_file_location("vendor_model_forensics_api", _VENDOR_API_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _cached = module
    return module
