#!/usr/bin/env bash
# Runs the backend locally in debug mode with auto-reload (SERVER_RELOAD
# defaults to true in config/settings.py) so backend code edits pick up
# without restarting the process. Serves on http://localhost:8000, matching
# the Flutter app's default API_BASE_URL.
set -e
cd "$(dirname "$0")"
exec .venv/bin/python main.py
