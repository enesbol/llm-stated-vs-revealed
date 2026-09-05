#!/usr/bin/env bash
# Thin wrapper -- all logic lives in stated_vs_revealed/reproduce.py.
set -euo pipefail
exec python -m stated_vs_revealed.reproduce "$@"
