#!/usr/bin/env bash
# Linux: run (or double-click in your file manager) to open the HOMES dashboard.
cd "$(dirname "$0")/../.." || exit 1
exec python3 dashboard/homes_dashboard.py "$@"
