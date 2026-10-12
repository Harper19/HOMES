#!/bin/zsh -l
# macOS: double-click to open the HOMES dashboard (no install needed).
cd "$(dirname "$0")/../.." || exit 1
python3 dashboard/homes_dashboard.py
