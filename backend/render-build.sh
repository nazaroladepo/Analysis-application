#!/usr/bin/env bash
set -euo pipefail

echo "🚧 Render build starting..."

# # Get the backend directory (where this script is located)
# BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# # PROJECT_ROOT="$(cd "$BACKEND_DIR/.." && pwd)"
# cd "$BACKEND_DIR"

echo "📦 Python: installing dependencies from requirements.txt"
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Render build completed successfully"
